import { app } from "../../scripts/app.js";

const EXTENSION_NAME = "localwildcards.insert";
const NODE_NAME = "LocalWildcardText";
const PLACEHOLDER = "Select wildcard to insert";
const NO_WILDCARDS = "No wildcards found";
const HEADER_PREFIX = "•";

function findWidget(node, widgetName) {
    if (!node || !node.widgets) {
        return null;
    }

    return node.widgets.find((widget) => widget.name === widgetName) || null;
}

function findTextareaFromWidget(widget) {
    if (!widget) {
        return null;
    }

    const possibleElements = [
        widget.inputEl,
        widget.element,
        widget.textarea,
        widget.domElement,
        widget.inputElement,
    ];

    for (const element of possibleElements) {
        if (!element) {
            continue;
        }

        if (
            element.tagName &&
            element.tagName.toLowerCase() === "textarea"
        ) {
            return element;
        }

        if (element.querySelector) {
            const textarea = element.querySelector("textarea");

            if (textarea) {
                return textarea;
            }
        }
    }

    return null;
}

function saveCursorPosition(node) {
    const textWidget = findWidget(node, "text");
    const textarea = findTextareaFromWidget(textWidget);

    if (!textarea) {
        return;
    }

    if (
        typeof textarea.selectionStart === "number" &&
        typeof textarea.selectionEnd === "number"
    ) {
        node.__localWildcardsCursor = {
            start: textarea.selectionStart,
            end: textarea.selectionEnd,
        };
    }
}

function attachCursorTracking(node) {
    const textWidget = findWidget(node, "text");

    if (!textWidget) {
        return;
    }

    let tries = 0;

    const tryAttach = () => {
        tries += 1;

        const textarea = findTextareaFromWidget(textWidget);

        if (!textarea) {
            if (tries < 60) {
                setTimeout(tryAttach, 250);
            }

            return;
        }

        if (textarea.__localWildcardsTrackingAttached) {
            return;
        }

        textarea.__localWildcardsTrackingAttached = true;

        const events = [
            "click",
            "keyup",
            "mouseup",
            "input",
            "select",
            "focus",
            "blur",
        ];

        for (const eventName of events) {
            textarea.addEventListener(eventName, () => {
                saveCursorPosition(node);
            });
        }

        saveCursorPosition(node);
    };

    tryAttach();
}

function makeTokenWithSpaces(oldText, start, end, token) {
    const before = oldText.slice(0, start);
    const after = oldText.slice(end);

    let insertText = String(token || "").trim();

    if (!insertText) {
        return {
            text: oldText,
            cursor: start,
        };
    }

    const needsSpaceBefore = before.length === 0 || !/\s$/.test(before);
    const needsSpaceAfter = after.length === 0 || !/^\s/.test(after);

    if (needsSpaceBefore) {
        insertText = " " + insertText;
    }

    if (needsSpaceAfter) {
        insertText = insertText + " ";
    }

    return {
        text: before + insertText + after,
        cursor: start + insertText.length,
    };
}

function setTextWidgetValue(node, textWidget, newText) {
    textWidget.value = newText;

    if (typeof textWidget.callback === "function") {
        textWidget.callback(newText);
    }

    if (node.onWidgetChanged) {
        node.onWidgetChanged(textWidget.name, newText, textWidget.value, textWidget);
    }

    if (app.canvas) {
        app.canvas.setDirty(true, true);
    }
}

function insertTextAtCursor(node, token) {
    const textWidget = findWidget(node, "text");

    if (!textWidget) {
        console.warn("[ComfyUI Local Wildcards] Text widget not found.");
        return;
    }

    const textarea = findTextareaFromWidget(textWidget);
    const oldText = String(textWidget.value || "");

    let start = oldText.length;
    let end = oldText.length;

    if (
        node.__localWildcardsCursor &&
        typeof node.__localWildcardsCursor.start === "number" &&
        typeof node.__localWildcardsCursor.end === "number"
    ) {
        start = node.__localWildcardsCursor.start;
        end = node.__localWildcardsCursor.end;
    } else if (
        textarea &&
        typeof textarea.selectionStart === "number" &&
        typeof textarea.selectionEnd === "number"
    ) {
        start = textarea.selectionStart;
        end = textarea.selectionEnd;
    }

    start = Math.max(0, Math.min(start, oldText.length));
    end = Math.max(0, Math.min(end, oldText.length));

    const result = makeTokenWithSpaces(oldText, start, end, token);

    setTextWidgetValue(node, textWidget, result.text);

    if (textarea) {
        textarea.value = result.text;
        textarea.selectionStart = result.cursor;
        textarea.selectionEnd = result.cursor;
        textarea.dispatchEvent(new Event("input", { bubbles: true }));
        textarea.focus();

        node.__localWildcardsCursor = {
            start: result.cursor,
            end: result.cursor,
        };
    }
}

function isWildcardToken(value) {
    const trimmedValue = String(value || "").trim();

    if (!trimmedValue) {
        return false;
    }

    if (trimmedValue === PLACEHOLDER) {
        return false;
    }

    if (trimmedValue === NO_WILDCARDS) {
        return false;
    }

    if (trimmedValue.startsWith("Too many wildcards")) {
        return false;
    }

    if (trimmedValue.startsWith(HEADER_PREFIX)) {
        return false;
    }

    if (!trimmedValue.startsWith("__")) {
        return false;
    }

    if (!trimmedValue.endsWith("__")) {
        return false;
    }

    return true;
}

app.registerExtension({
    name: EXTENSION_NAME,

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== NODE_NAME) {
            return;
        }

        const originalOnNodeCreated = nodeType.prototype.onNodeCreated;

        nodeType.prototype.onNodeCreated = function () {
            if (originalOnNodeCreated) {
                originalOnNodeCreated.apply(this, arguments);
            }

            const node = this;

            attachCursorTracking(node);

            setTimeout(() => {
                attachCursorTracking(node);
            }, 1000);

            const insertWidget = findWidget(node, "insert_wildcard");

            if (!insertWidget) {
                console.warn("[ComfyUI Local Wildcards] insert_wildcard widget not found.");
                return;
            }

            const originalCallback = insertWidget.callback;

            insertWidget.callback = function (value) {
                if (originalCallback) {
                    originalCallback.apply(this, arguments);
                }

                const trimmedValue = String(value || "").trim();

                if (!isWildcardToken(trimmedValue)) {
                    insertWidget.value = PLACEHOLDER;

                    if (app.canvas) {
                        app.canvas.setDirty(true, true);
                    }

                    return;
                }

                insertTextAtCursor(node, trimmedValue);

                insertWidget.value = PLACEHOLDER;

                if (app.canvas) {
                    app.canvas.setDirty(true, true);
                }
            };
        };
    },
});