import { Chart, type ChartType } from "chart.js";
import { AbstractGraph } from "./abstract";
import { getPlayTimeEndDate, getPlayTimeStartDate } from "./utils";

export default class EpisodePlaysGraph extends AbstractGraph {
    graphType: string = "episode-plays";

    getDefaultDates(): [Date, Date] {
        return [getPlayTimeStartDate(), getPlayTimeEndDate()];
    }

    async renderChart(): Promise<Chart> {
        const json = await this.getApiResponse();
        const chartType = (this.canvas.dataset.chartType || "bar") as ChartType;

        return new Chart(this.canvas, {
            type: chartType,
            data: {
                datasets: json.datasets,
            },
            options: {
                maintainAspectRatio: false,
                parsing: false,
                plugins: {
                    legend: {
                        display: false,
                    },
                    tooltip: {
                        itemSort: (a, b) => {
                            return b.parsed.y - a.parsed.y;
                        },
                    },
                },
                scales: {
                    x: {
                        type: "time",
                        stacked: true,
                        time: this.getTimeScaleTimeOptions(),
                        ticks: {
                            maxRotation: this.episode ? 0 : 20,
                        },
                    },
                    y: {
                        beginAtZero: true,
                        stacked: true,
                    },
                },
                datasets: {
                    bar: {
                        barPercentage: 1.0,
                        categoryPercentage: 1.0,
                    },
                    line: {
                        tension: 0.25,
                    },
                },
            },
        });
    }
}
