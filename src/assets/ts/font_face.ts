function getFontSampleInput(): HTMLInputElement | undefined {
    const elem = document.getElementById("font-sample-input");

    if (elem instanceof HTMLInputElement) return elem;
    return;
}

function getFontSampleOutput(): HTMLElement | undefined {
    return document.getElementById("font-sample");
}

function getFontSampleSizeInput(): HTMLInputElement | undefined {
    const elem = document.getElementById("font-sample-size");

    if (elem instanceof HTMLInputElement) return elem;
    return;
}

function getWeightSelect(): HTMLSelectElement | undefined {
    const elem = document.getElementById("id_weight");

    if (elem instanceof HTMLSelectElement) return elem;
    return;
}

export function initFontSampleInput() {
    const sample = getFontSampleOutput();
    const sampleInput = getFontSampleInput();
    const weightSelect = getWeightSelect();
    const sampleSizeInput = getFontSampleSizeInput();

    if (sample) {
        if (sampleInput) {
            sampleInput.addEventListener("input", () => {
                sample.textContent = sampleInput.value;
            });
        }
        if (weightSelect) {
            weightSelect.addEventListener("change", () => {
                if (weightSelect.selectedOptions.length > 0) {
                    sample.style.fontWeight = weightSelect.selectedOptions.item(0).value;
                }
            });
        }
        if (sampleSizeInput) {
            const changeFontSize = () => {
                if (!isNaN(sampleSizeInput.valueAsNumber)) {
                    sample.style.fontSize = `${sampleSizeInput.valueAsNumber}px`;
                }
            };

            sampleSizeInput.addEventListener("input", changeFontSize);
            changeFontSize();
        }
    }
}
