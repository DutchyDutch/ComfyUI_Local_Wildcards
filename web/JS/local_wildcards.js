import { app } from "../../scripts/app.js";

const EXTENSION_NAME = "localwildcards.insert";
const NODE_NAME = "LocalWildcardText";
const PLACEHOLDER = "Select wildcard to insert";
const NO_WILDCARDS = "No wildcards found";
const HEADER_PREFIX = "•";

const PREVIEW_PLACEHOLDER_TEXT = "Wildcard preview will appear here after you run the node.";

// Small safety buffer added to computed node heights, so that
// minor layout measurement timing differences never cause the
// bottom border of the preview box to get visually clipped.
const HEIGHT_SAFETY_BUFFER_PX = 8;

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

function resizeNodeToFitWidgets(node) {
    try {
        if (typeof node.computeSize === "function" && typeof node.setSize === "function") {
            const currentHeight = node.size ? node.size[1] : 0;
            const computedSize = node.computeSize();

            if (computedSize) {
                const targetHeight = computedSize[1] + HEIGHT_SAFETY_BUFFER_PX;

                if (targetHeight > currentHeight) {
                    node.setSize([node.size[0], targetHeight]);
                }
            }
        }
    } catch (error) {
        console.warn("[ComfyUI Local Wildcards] Could not resize node:", error);
    }

    if (app.canvas) {
        app.canvas.setDirty(true, true);
    }
}

function captureMinimumNodeSize(node) {
    try {
        if (typeof node.computeSize === "function") {
            const computedSize = node.computeSize();

            if (computedSize) {
                // Store this as the smallest the node is allowed to be,
                // including the same safety buffer used elsewhere so the
                // enforced minimum never clips the preview box border.
                node.__localWildcardsMinSize = [
                    computedSize[0],
                    computedSize[1] + HEIGHT_SAFETY_BUFFER_PX,
                ];
            }
        }
    } catch (error) {
        console.warn("[ComfyUI Local Wildcards] Could not capture minimum size:", error);
    }
}

function enforceMinimumNodeSize(node) {
    if (!node.__localWildcardsMinSize || !node.size) {
        return;
    }

    const minSize = node.__localWildcardsMinSize;

    let width = node.size[0];
    let height = node.size[1];
    let changed = false;

    if (width < minSize[0]) {
        width = minSize[0];
        changed = true;
    }

    if (height < minSize[1]) {
        height = minSize[1];
        changed = true;
    }

    if (changed) {
        node.size[0] = width;
        node.size[1] = height;

        if (app.canvas) {
            app.canvas.setDirty(true, true);
        }
    }
}

function attachMinimumSizeEnforcement(node) {
    if (node.__localWildcardsMinSizeAttached) {
        return;
    }

    node.__localWildcardsMinSizeAttached = true;

    const originalOnResize = node.onResize;

    node.onResize = function (size) {
        if (originalOnResize) {
            originalOnResize.apply(this, arguments);
        }

        enforceMinimumNodeSize(node);
    };
}

function settleNodeSizing(node) {
    // Loaded workflows and freshly-dragged nodes can settle their DOM
    // layout at slightly different times. Re-checking the size a few
    // times over roughly the first two seconds (instead of trusting
    // only the very first measurement) reliably avoids the bottom
    // border being clipped, regardless of how the node was created.
    const delays = [0, 50, 150, 300, 600, 1000, 2000];

    for (const delay of delays) {
        setTimeout(() => {
            resizeNodeToFitWidgets(node);
            captureMinimumNodeSize(node);
        }, delay);
    }
}

function setPreviewPlaceholder(container) {
    container.textContent = PREVIEW_PLACEHOLDER_TEXT;
    container.style.fontStyle = "italic";
    container.style.opacity = "0.6";
}

function setPreviewContent(container, text) {
    container.textContent = String(text || "");
    container.style.fontStyle = "normal";
    container.style.opacity = "1";
}

function ensurePreviewElement(node) {
    if (node.__localWildcardsPreviewEl) {
        return node.__localWildcardsPreviewEl;
    }

    const container = document.createElement("div");

    container.className = "local-wildcards-preview";
    container.style.width = "100%";
    container.style.minHeight = "48px";
    container.style.maxHeight = "220px";
    container.style.overflowY = "auto";
    container.style.whiteSpace = "pre-wrap";
    container.style.wordBreak = "break-word";
    container.style.padding = "6px 8px";
    container.style.boxSizing = "border-box";
    container.style.fontFamily = "inherit";
    container.style.fontSize = "12px";
    container.style.lineHeight = "1.4";
    container.style.color = "#dddddd";
    container.style.background = "rgba(0, 0, 0, 0.3)";
    container.style.border = "1px solid rgba(255, 255, 255, 0.15)";
    container.style.borderRadius = "6px";
    container.style.userSelect = "text";

    if (typeof node.addDOMWidget !== "function") {
        console.warn(
            "[ComfyUI Local Wildcards] addDOMWidget is not available on this ComfyUI version. Preview box cannot be created.",
        );
        return null;
    }

    try {
        node.addDOMWidget(
            "expanded_text_preview",
            "customtext",
            container,
            {
                serialize: false,
                getMinHeight: () => 48 + HEIGHT_SAFETY_BUFFER_PX,
                getMaxHeight: () => 220,
            },
        );
    } catch (error) {
        console.warn("[ComfyUI Local Wildcards] addDOMWidget failed:", error);
        return null;
    }

    setPreviewPlaceholder(container);

    node.__localWildcardsPreviewEl = container;

    attachMinimumSizeEnforcement(node);
    settleNodeSizing(node);

    return container;
}

function showExpandedText(node, boldDisplayText) {
    try {
        const container = ensurePreviewElement(node);

        if (!container) {
            return;
        }

        setPreviewContent(container, boldDisplayText);

        resizeNodeToFitWidgets(node);
    } catch (error) {
        console.warn("[ComfyUI Local Wildcards] Could not show preview:", error);
    }
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

            // Create the preview box right away, with a placeholder
            // message, so it's visible immediately instead of only
            // appearing after the node has been run once. This also
            // schedules the repeated size checks that prevent the
            // bottom border from being clipped on workflow load.
            ensurePreviewElement(node);

            const originalOnExecuted = node.onExecuted;

            node.onExecuted = function (message) {
                if (originalOnExecuted) {
                    originalOnExecuted.apply(this, arguments);
                }

                const expandedText = message?.expanded_text?.[0] ?? "";

                showExpandedText(node, expandedText);
            };

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
