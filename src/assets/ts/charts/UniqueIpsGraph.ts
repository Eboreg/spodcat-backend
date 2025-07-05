import { Chart } from "chart.js";
import type { ChartApiResponse } from "../types";
import { AbstractGraph } from "./abstract";

export default class UniqueIpsGraph extends AbstractGraph {
    chartType: string;
    title: string;

    constructor(canvas: HTMLCanvasElement, chartType: string, title: string) {
        super(canvas);
        this.chartType = chartType;
        this.title = title;
    }

    async getApiResponse(): Promise<ChartApiResponse> {
        const now = new Date();
        const end = new Date(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate())).toISOString().slice(0, 10);
        const start = new Date(Date.UTC(now.getFullYear(), now.getMonth() - 5, 1)).toISOString().slice(0, 10);
        const response = await fetch(this.getUrl(`/podcasts/chart/?start=${start}&end=${end}&type=${this.chartType}`));

        return response.json();
    }

    async render(): Promise<Chart> {
        const json = await this.getApiResponse();

        return new Chart(this.canvas, {
            type: "line",
            data: {
                datasets: json.datasets,
            },
            options: {
                maintainAspectRatio: false,
                parsing: false,
                plugins: {
                    title: {
                        text: this.title,
                        display: true,
                    },
                },
                scales: {
                    x: {
                        type: "time",
                        stacked: true,
                        time: {
                            unit: "month",
                            tooltipFormat: "MMM yyyy",
                        },
                    },
                    y: {
                        beginAtZero: true,
                        stacked: false,
                    },
                },
                datasets: {
                    line: {
                        tension: 0,
                    },
                },
            },
        });
    }
}
