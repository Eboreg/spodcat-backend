import { Chart } from "chart.js";
import type { ChartApiResponse } from "../types";
import { AbstractEpisodePlaysGraph } from "./abstract";
import { getContext } from "./utils";

export default class EpisodePlaysGraph extends AbstractEpisodePlaysGraph {
    podcastSlug: string;
    podcastName: string;

    constructor(canvas: HTMLCanvasElement, podcastSlug: string, podcastName: string) {
        super(canvas);
        this.podcastName = podcastName;
        this.podcastSlug = podcastSlug;
    }

    async getApiResponse(startDate: Date, endDate: Date): Promise<ChartApiResponse> {
        const start = startDate.toISOString().slice(0, 10);
        const end = endDate.toISOString().slice(0, 10);
        const url = this.getUrl(`/podcasts/${this.podcastSlug}/chart/?start=${start}&end=${end}&type=play-time`);
        const response = await fetch(url);

        return response.json();
    }

    async renderChart(startDate: Date, endDate: Date): Promise<Chart> {
        const json: ChartApiResponse = await this.getApiResponse(startDate, endDate);
        const context = getContext();

        return new Chart(this.canvas, {
            type: "bar",
            data: {
                datasets: json.datasets,
            },
            options: {
                maintainAspectRatio: false,
                parsing: false,
                plugins: {
                    title: {
                        text: `${this.podcastName}: ` + context.strings.episodePlayTimeTitle,
                        display: true,
                    },
                    legend: {
                        display: false,
                    },
                },
                scales: {
                    x: {
                        type: "time",
                        min: startDate.getTime() + startDate.getTimezoneOffset() * 60_000,
                        max: endDate.getTime() + endDate.getTimezoneOffset() * 60_000,
                        stacked: true,
                        time: {
                            minUnit: "day",
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
                },
            },
        });
    }
}
