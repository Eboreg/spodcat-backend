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
// Chart.defaults.datasets.line.spanGaps = true;
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

function formatDuration(totalSeconds: number) {
    const hours = Math.floor(totalSeconds / 60 / 60);
    const minutes = Math.floor((totalSeconds / 60) % 60);
    const seconds = Math.floor(totalSeconds % 60);

    if (hours) return `${hours}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
    return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

export async function renderEpisodePlayTimeGraph(
    canvas: HTMLCanvasElement,
    podcastSlug: string,
    podcastName: string,
    startDate?: Date,
    endDate?: Date
): Promise<Chart> {
    const now = new Date();

    startDate = startDate || new Date(now.getFullYear(), now.getMonth(), now.getDate() - 30);
    endDate = endDate || new Date(now.getFullYear(), now.getMonth(), now.getDate());
    startDate.setMinutes(-startDate.getTimezoneOffset());
    endDate.setMinutes(-endDate.getTimezoneOffset());

    const start = startDate.toISOString().slice(0, 10);
    const end = endDate.toISOString().slice(0, 10);
    const url = `/podcasts/${podcastSlug}/episode_chart/?start=${start}&end=${end}`;
    const response = await fetch(url);
    const json: ChartApiResponse = await response.json();

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
                    text: `${podcastName}: Daily play time per episode`,
                    display: true,
                },
                legend: {
                    display: false,
                },
            },
            scales: {
                x: {
                    type: "time",
                    min: startDate.getTime(),
                    max: endDate.getTime(),
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
    endDate: Date
): Promise<Chart> {
    const start = startDate.toISOString().slice(0, 10);
    const end = endDate.toISOString().slice(0, 10);
    const response = await fetch(`/podcasts/chart/?start=${start}&end=${end}`);
    const json: ChartApiResponse = await response.json();

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
                    text: "Daily play time per podcast",
                    display: true,
                },
            },
            scales: {
                x: {
                    type: "time",
                    min: startDate.getTime(),
                    max: endDate.getTime(),
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
    const now = new Date();
    const startDate = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 30, 0, -now.getTimezoneOffset());
    const endDate = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, -now.getTimezoneOffset());
    const startElem = canvas.parentElement.querySelector("input[name=start]");
    const endElem = canvas.parentElement.querySelector("input[name=end]");

    let graph = await render(startDate, endDate);

    if (startElem instanceof HTMLInputElement && endElem instanceof HTMLInputElement) {
        startElem.valueAsDate = startDate;
        endElem.valueAsDate = endDate;
        endElem.min = startElem.value;
        startElem.max = endElem.value;

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
        return renderPodcastPlayTimeGraph(podcastPlayTimeCanvas, startDate, endDate);
    });
}

document.querySelectorAll(".episode-play-time-chart").forEach((element) => {
    if (element instanceof HTMLCanvasElement && element.dataset.podcastSlug) {
        initPlayTimeGraph(element, async (startDate, endDate) => {
            return renderEpisodePlayTimeGraph(
                element,
                element.dataset.podcastSlug,
                element.dataset.podcastName,
                startDate,
                endDate,
            );
        });
    }
});
