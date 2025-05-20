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

addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".inline-related input").forEach((input) => {
        input.addEventListener("change", onInlineValueChange);
    })
});

addEventListener("formset:added", (event) => {
    if (event.target instanceof Element) {
        event.target.querySelectorAll("input").forEach((input) => {
            input.addEventListener("change", onInlineValueChange);
        });
    }
});
