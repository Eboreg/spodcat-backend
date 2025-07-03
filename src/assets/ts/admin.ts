import { initFontSampleInput } from "./font_face";

function formatTimestamp(value: string) {
    value = value.trim();
    const parts = value.split(":");

    if (!value) return value;
    while (parts.length < 3) {
        parts.splice(0, 0, "0");
    }
    for (let idx = 1; idx < parts.length; idx++) {
        const part = parseInt(parts[idx]);

        if (isNaN(part)) return value;
        parts[idx] = part.toLocaleString(undefined, { minimumIntegerDigits: 2 });
    }
    return parts.join(":");
}

function clickInlineAddButton(child: Element) {
    child.closest(".inline-related")?.querySelector(".add-row a")?.dispatchEvent(new Event("click"));
}

function isLastInlineRow(child: Element): boolean {
    const row = child.closest(".form-row");
    const nextRow = row?.nextElementSibling;

    return nextRow == null || !nextRow.classList.contains("form-row") || nextRow.classList.contains("empty-form");
}

function onInlineValueChange(event: Event) {
    if (event.target instanceof Element && isLastInlineRow(event.target)) {
        clickInlineAddButton(event.target);
    }
}

function onTimestampFieldChange(event: Event) {
    if (event.target instanceof HTMLInputElement) {
        event.target.value = formatTimestamp(event.target.value);
    }
}

addEventListener("DOMContentLoaded", () => {
    initFontSampleInput();
    document.querySelectorAll(".inline-related input").forEach((input) => {
        input.addEventListener("change", onInlineValueChange);
    });
    document.querySelectorAll(".timestamp-field").forEach((input) => {
        input.addEventListener("change", onTimestampFieldChange);
    });
});

addEventListener("formset:added", (event) => {
    if (event.target instanceof Element) {
        event.target.querySelectorAll("input").forEach((input) => {
            input.addEventListener("change", onInlineValueChange);
        });
        event.target.querySelectorAll(".timestamp-field").forEach((input) => {
            input.addEventListener("change", onTimestampFieldChange);
        });
    }
});
