function getFontSampleInput(): HTMLInputElement | undefined {
    const elem = document.getElementById("font-sample-input");

    if (elem instanceof HTMLInputElement) return elem;
    return;
}

function getFontSampleOutput(): HTMLElement | undefined {
    return document.querySelector(".font-sample-output");
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

export function initPodcastNameFontSample() {
    const fontSelect = document.querySelector(".model-podcast.change-form #id_name_font_face");
    const sizeSelect = document.querySelector(".model-podcast.change-form #id_name_font_size");
    const nameInput = document.querySelector(".model-podcast.change-form #id_name");
    const sample = getFontSampleOutput();

    if (sample) {
        if (fontSelect instanceof HTMLSelectElement) {
            const changeFontFamily = () => {
                const family = '"' + fontSelect.options.item(fontSelect.selectedIndex).text + '"';
                sample.style.fontFamily = family;
            };

            changeFontFamily();
            fontSelect.addEventListener("change", changeFontFamily);
        }

        if (sizeSelect instanceof HTMLSelectElement) {
            const changeFontSize = () => {
                const size = sizeSelect.options.item(sizeSelect.selectedIndex).value;

                if (size == "small") sample.style.fontSize = "35px";
                else if (size == "normal") sample.style.fontSize = "50px";
                else if (size == "large") sample.style.fontSize = "70px";
            };

            changeFontSize();
            sizeSelect.addEventListener("change", changeFontSize);
        }

        if (nameInput instanceof HTMLInputElement) {
            const changeText = () => {
                sample.textContent = nameInput.value;
            }

            changeText();
            nameInput.addEventListener("input", changeText);
        }
    }
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
