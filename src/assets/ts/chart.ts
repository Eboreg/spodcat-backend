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

interface ColorConfig {
    borderColor: string;
    backgroundColor: string;
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
    Legend
);

Chart.defaults.color = "#eeeeee";
Chart.defaults.borderColor = "#ff882244";
Chart.defaults.datasets.line.fill = "start";
Chart.defaults.animation = false;
Chart.defaults.datasets.line.normalized = true;
Chart.defaults.datasets.line.spanGaps = true;
Chart.defaults.scales.time.time.tooltipFormat = "yyyy-MM-dd";
Chart.defaults.interaction = {
    mode: "nearest",
    axis: "x",
    intersect: false,
    includeInvisible: false,
};

const colorConfigs: ColorConfig[] = [
    {
        borderColor: "rgb(75, 192, 192)",
        backgroundColor: "rgba(75, 192, 192, 0.3)",
    },
    {
        borderColor: "rgb(192, 75, 192)",
        backgroundColor: "rgba(192, 75, 192, 0.3)",
    },
    {
        borderColor: "rgb(192, 192, 75)",
        backgroundColor: "rgba(192, 192, 75, 0.3)",
    },
];

function formatDuration(totalSeconds: number) {
    const hours = Math.floor(totalSeconds / 60 / 60);
    const minutes = Math.floor((totalSeconds / 60) % 60);
    const seconds = Math.floor(totalSeconds % 60);

    if (hours) return `${hours}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
    return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

function getColorConfig(idx: number): ColorConfig {
    return colorConfigs[idx % colorConfigs.length];
}

export async function renderPodcastPlayTimeGraph(canvas: HTMLCanvasElement, startDate?: Date, endDate?: Date) {
    let colorConfigIdx = 0;
    const now = new Date();

    startDate = startDate || new Date(now.getFullYear(), now.getMonth(), now.getDate() - 30);
    endDate = endDate || new Date(now.getFullYear(), now.getMonth(), now.getDate());
    startDate.setMinutes(-startDate.getTimezoneOffset());
    endDate.setMinutes(-endDate.getTimezoneOffset());

    const url = `/podcasts/chart/?start=${startDate.toISOString().slice(0, 10)}&end=${endDate
        .toISOString()
        .slice(0, 10)}`;
    const response = await fetch(url);
    const json: ChartApiResponse = await response.json();
    const datasets = json.datasets.map((d) => {
        return { ...d, ...getColorConfig(colorConfigIdx++) };
    });

    new Chart(canvas, {
        type: "line",
        data: {
            datasets: datasets,
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
                    time: {
                        round: "day",
                        unit: "day",
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

const podcastPlayTimeCanvas = document.getElementById("podcast-play-time-chart");

if (podcastPlayTimeCanvas instanceof HTMLCanvasElement) {
    renderPodcastPlayTimeGraph(podcastPlayTimeCanvas);
}
