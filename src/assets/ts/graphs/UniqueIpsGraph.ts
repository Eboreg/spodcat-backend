import { Chart } from "chart.js";
import { AbstractGraph } from "./abstract";
import type { GraphApiResponse } from "../types";

export default class UniqueIpsGraph extends AbstractGraph {
    constructor(canvas: HTMLCanvasElement, graphType: string, startInput?: Element, endInput?: Element) {
        super(canvas, startInput, endInput);
        this.graphType = graphType;
    }

    getDefaultDates(): [Date, Date] {
        const now = new Date();

        return [
            new Date(Date.UTC(now.getFullYear(), now.getMonth() - 5, 1)),
            new Date(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate())),
        ];
    }

    renderChart(json: GraphApiResponse): Chart {
        return new Chart(this.canvas, {
            type: "line",
            data: {
                datasets: json.datasets,
            },
            options: {
                plugins: {
                    legend: {
                        display: this.canvas.dataset.podcast == undefined && this.canvas.dataset.episode == undefined,
                        position: "chartArea",
                    },
                },
                scales: {
                    x: {
                        type: "time",
                        stacked: true,
                        time: this.getTimeScaleTimeOptions(),
                        ticks: {
                            maxRotation: 0,
                        },
                    },
                    y: {
                        beginAtZero: true,
                        stacked: false,
                    },
                },
            },
        });
    }
}
