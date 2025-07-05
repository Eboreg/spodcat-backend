function checkStartDate(date: Date): Date {
    const earliestDate = getEarliestDate();

    if (earliestDate.getTime() > date.getTime()) return earliestDate;
    return date;
}

function getOrSetDate(inputName: string, fallback: Date): Date {
    const input = document.querySelector(`input[name=${inputName}]`);

    if (input instanceof HTMLInputElement) {
        if (!input.valueAsDate) input.valueAsDate = fallback;
        return input.valueAsDate;
    }
    return fallback;
}

export function getContext() {
    return JSON.parse(document.getElementById("context")?.textContent || "{}");
}

export function getEarliestDate(): Date {
    return new Date(Date.UTC(2025, 4, 1));
}

export function getPlayTimeEndDate(): Date {
    const now = new Date();
    const endDate = new Date(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()));

    return getOrSetDate("daily-plays-end-date", endDate);
}

export function getPlayTimeStartDate(): Date {
    const now = new Date();
    const startDate = checkStartDate(new Date(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate() - 30)));

    return getOrSetDate("daily-plays-start-date", startDate);
}
