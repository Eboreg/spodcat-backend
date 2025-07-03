import {
    Chart,
    LineController,
    TimeScale,
    LinearScale,
    PointElement,
    LineElement,
    Filler,
    Tooltip,
    Decimation,
    Title,
    Legend,
    Colors,
    BarController,
    BarElement,
} from "chart.js";
import "chartjs-adapter-date-fns";

interface ChartApiResponse {
    datasets: {
        label: string;
        data: {
            x: number;
            y: number;
        }[];
    }[];
}

Chart.register(
    LineController,
    TimeScale,
    LinearScale,
    PointElement,
    LineElement,
    Filler,
    Tooltip,
    Decimation,
    Title,
    Legend,
    Colors,
    BarController,
    BarElement
);

Chart.defaults.color = "#eeeeee";
Chart.defaults.borderColor = "#ff882244";
Chart.defaults.datasets.line.fill = "start";
Chart.defaults.animation = false;
Chart.defaults.datasets.line.normalized = true;
Chart.defaults.datasets.line.tension = 0.25;
Chart.defaults.scales.time.time.tooltipFormat = "yyyy-MM-dd";
Chart.defaults.plugins.colors = {
    enabled: true,
    forceOverride: true,
};
Chart.defaults.interaction = {
    mode: "nearest",
    axis: "x",
    intersect: false,
    includeInvisible: false,
};

function getEarliestDate(): Date {
    return new Date(Date.UTC(2025, 4, 1));
}

function checkStartDate(date: Date): Date {
    const earliestDate = getEarliestDate();

    if (earliestDate.getTime() > date.getTime()) return earliestDate;
    return date;
}

function formatDuration(totalSeconds: number) {
    const hours = Math.floor(totalSeconds / 60 / 60);
    const minutes = Math.floor((totalSeconds / 60) % 60);
    const seconds = Math.floor(totalSeconds % 60);

    if (hours) return `${hours}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
    return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

function getContext() {
    return JSON.parse(document.getElementById("context")?.textContent || "{}");
}

function getUrl(path: string) {
    const root: string = getContext().rootPath || "";

    return root.replace(/\/$/, "") + "/" + path.replace(/^\//, "");
}

export async function renderEpisodePlayTimeGraph(
    canvas: HTMLCanvasElement,
    podcastSlug: string,
    podcastName: string,
    startDate: Date,
    endDate: Date
): Promise<Chart> {
    const start = startDate.toISOString().slice(0, 10);
    const end = endDate.toISOString().slice(0, 10);
    const url = getUrl(`/podcasts/${podcastSlug}/episode_chart/?start=${start}&end=${end}`);
    const response = await fetch(url);
    const json: ChartApiResponse = await response.json();
    const context = getContext();

    return new Chart(canvas, {
        type: "bar",
        data: {
            datasets: json.datasets,
        },
        options: {
            maintainAspectRatio: false,
            parsing: false,
            plugins: {
                tooltip: {
                    callbacks: {
                        label: (item) => {
                            return item.dataset.label + ": " + formatDuration(item.parsed.y);
                        },
                    },
                },
                title: {
                    text: `${podcastName}: ` + context.strings.episodePlayTimeTitle,
                    display: true,
                },
                legend: {
                    display: false,
                },
            },
            scales: {
                x: {
                    type: "time",
                    min: startDate.getTime() + (startDate.getTimezoneOffset() * 60_000),
                    max: endDate.getTime() + (endDate.getTimezoneOffset() * 60_000),
                    ticks: {
                        source: "auto",
                    },
                    stacked: true,
                    time: {
                        minUnit: "day",
                    },
                },
                y: {
                    min: 0,
                    title: {
                        text: "H:MM:SS",
                        display: true,
                    },
                    ticks: {
                        callback: (tickValue) => {
                            if (typeof tickValue == "string") return formatDuration(parseInt(tickValue));
                            return formatDuration(tickValue);
                        },
                    },
                    beginAtZero: true,
                    stacked: true,
                },
            },
            datasets: {
                bar: {
                    barPercentage: 1.0,
                    categoryPercentage: 1.0,
                },
            },
        },
    });
}

export async function renderPodcastPlayTimeGraph(
    canvas: HTMLCanvasElement,
    startDate: Date,
    endDate: Date,
): Promise<Chart> {
    const start = startDate.toISOString().slice(0, 10);
    const end = endDate.toISOString().slice(0, 10);
    const response = await fetch(getUrl(`/podcasts/chart/?start=${start}&end=${end}`));
    const json: ChartApiResponse = await response.json();
    const context = getContext();

    return new Chart(canvas, {
        type: "line",
        data: {
            datasets: json.datasets,
        },
        options: {
            maintainAspectRatio: false,
            parsing: false,
            plugins: {
                decimation: {
                    algorithm: "lttb",
                    enabled: true,
                    samples: 31,
                    threshold: 31,
                },
                tooltip: {
                    callbacks: {
                        label: (item) => {
                            return item.dataset.label + ": " + formatDuration(item.parsed.y);
                        },
                    },
                },
                title: {
                    text: context.strings.podcastPlayTimeTitle,
                    display: true,
                },
            },
            scales: {
                x: {
                    type: "time",
                    min: startDate.getTime() + (startDate.getTimezoneOffset() * 60_000),
                    max: endDate.getTime() + (endDate.getTimezoneOffset() * 60_000),
                    ticks: {
                        source: "auto",
                    },
                    stacked: true,
                    time: {
                        minUnit: "day",
                    },
                },
                y: {
                    min: 0,
                    title: {
                        text: "H:MM:SS",
                        display: true,
                    },
                    ticks: {
                        callback: (tickValue) => {
                            if (typeof tickValue == "string") return formatDuration(parseInt(tickValue));
                            return formatDuration(tickValue);
                        },
                    },
                },
            },
        },
    });
}

async function initPlayTimeGraph(
    canvas: HTMLCanvasElement,
    render: (startDate: Date, endDate: Date) => Promise<Chart>
) {
    const startElem = canvas.closest(".chart-container")?.querySelector("input[name=start]");
    const endElem = canvas.closest(".chart-container")?.querySelector("input[name=end]");

    const now = new Date();
    const earliestDate = getEarliestDate();
    const endDate = new Date(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()));
    const startDate = checkStartDate(new Date(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate() - 30)));

    let graph = await render(startDate, endDate);

    if (startElem instanceof HTMLInputElement && endElem instanceof HTMLInputElement) {
        startElem.valueAsDate = startDate;
        endElem.valueAsDate = endDate;
        endElem.min = startElem.value;
        endElem.max = endDate.toISOString().slice(0, 10);
        startElem.max = endElem.value;
        startElem.min = earliestDate.toISOString().slice(0, 10);

        startElem.addEventListener("change", async () => {
            graph.destroy();
            graph = await render(startElem.valueAsDate, endElem.valueAsDate);
            endElem.min = startElem.value;
        });
        endElem.addEventListener("change", async () => {
            graph.destroy();
            graph = await render(startElem.valueAsDate, endElem.valueAsDate);
            startElem.max = endElem.value;
        });
    }
}

const podcastPlayTimeCanvas = document.getElementById("podcast-play-time-chart");

if (podcastPlayTimeCanvas instanceof HTMLCanvasElement) {
    initPlayTimeGraph(podcastPlayTimeCanvas, async (startDate, endDate) => {
        return renderPodcastPlayTimeGraph(podcastPlayTimeCanvas, checkStartDate(startDate), endDate);
    });
}

document.querySelectorAll(".episode-play-time-chart").forEach((element) => {
    if (element instanceof HTMLCanvasElement && element.dataset.podcastSlug) {
        initPlayTimeGraph(element, async (startDate, endDate) => {
            return renderEpisodePlayTimeGraph(
                element,
                element.dataset.podcastSlug,
                element.dataset.podcastName,
                checkStartDate(startDate),
                endDate,
            );
        });
    }
});
