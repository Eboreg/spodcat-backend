import { Chart } from "chart.js";
import type { ChartApiResponse } from "../types";
import { AbstractEpisodePlaysGraph } from "./abstract";
import { getContext } from "./utils";

export default class PodcastEpisodePlaysGraph extends AbstractEpisodePlaysGraph {
    async getApiResponse(startDate: Date, endDate: Date): Promise<ChartApiResponse> {
        const start = startDate.toISOString().slice(0, 10);
        const end = endDate.toISOString().slice(0, 10);
        const response = await fetch(this.getUrl(`/podcasts/chart/?start=${start}&end=${end}&type=play-time`));

        return response.json();
    }

    async renderChart(startDate: Date, endDate: Date): Promise<Chart> {
        const json = await this.getApiResponse(startDate, endDate);
        const context = getContext();

        return new Chart(this.canvas, {
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
                    title: {
                        text: context.strings.podcastPlayTimeTitle,
                        display: true,
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
                    },
                },
            },
        });
    }
}
