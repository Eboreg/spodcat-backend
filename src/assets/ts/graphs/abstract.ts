import { Chart, type TimeScaleTimeOptions } from "chart.js";
import type { GraphApiResponse, TimePeriod } from "../types";

export abstract class AbstractGraph {
    canvas: HTMLCanvasElement;
    graphType: string;
    timePeriod: TimePeriod;
    startDate: Date;
    endDate: Date;

    chart?: Chart;
    podcast?: string;
    episode?: string;
    startInput?: HTMLInputElement;
    endInput?: HTMLInputElement;
    timePeriodSelect?: HTMLSelectElement;

    constructor(canvas: HTMLCanvasElement, startInput?: Element, endInput?: Element) {
        const timePeriodSelect = canvas.closest(".graph-container")?.querySelector(".time-period");
        const resetLink = canvas.closest(".graph-container")?.querySelector(".reset-link");

        this.canvas = canvas;
        this.podcast = canvas.dataset.podcast;
        this.episode = canvas.dataset.episode;
        this.timePeriod = canvas.dataset.period as TimePeriod;
        [this.startDate, this.endDate] = this.getDefaultDates();
        if (canvas.dataset.startDate) this.startDate = new Date(canvas.dataset.startDate);

        startInput = startInput || canvas.closest(".graph-container")?.querySelector(".start-date");
        endInput = endInput || canvas.closest(".graph-container")?.querySelector(".end-date");

        resetLink?.addEventListener("click", this.reset.bind(this));

        if (timePeriodSelect instanceof HTMLSelectElement) {
            this.timePeriodSelect = timePeriodSelect;
            timePeriodSelect.addEventListener("change", () => {
                this.timePeriod = timePeriodSelect.value as TimePeriod;
                this.render();
            });
        }

        if (startInput instanceof HTMLInputElement) {
            this.startInput = startInput;
            startInput.valueAsDate = this.startDate;
            startInput.max = this.endDate.toISOString().slice(0, 10);

            startInput.addEventListener("change", () => {
                if (startInput.valueAsDate) {
                    this.startDate = startInput.valueAsDate;
                    if (this.endInput) this.endInput.min = startInput.value;
                    this.render();
                }
            });
        }

        if (endInput instanceof HTMLInputElement) {
            this.endInput = endInput;
            endInput.valueAsDate = this.endDate;
            endInput.max = (new Date()).toISOString().slice(0, 10);
            endInput.min = this.startDate.toISOString().slice(0, 10);

            endInput.addEventListener("change", () => {
                if (endInput.valueAsDate) {
                    this.endDate = endInput.valueAsDate;
                    if (this.startInput) this.startInput.max = endInput.value;
                    this.render();
                }
            });
        }
    }

    async getApiResponse(extraParams: Record<string, string> = {}): Promise<GraphApiResponse> {
        const url = this.getUrl("/graph/");
        const params = new URLSearchParams({
            type: this.graphType,
            start: this.startDate.toISOString().slice(0, 10),
            end: this.endDate.toISOString().slice(0, 10),
            period: this.timePeriod,
            ...extraParams,
        });

        if (this.podcast) params.append("podcast", this.podcast);
        if (this.episode) params.append("episode", this.episode);

        const response = await fetch(`${url}?${params}`);

        return response.json();
    }

    getTimeScaleTimeOptions(): Partial<TimeScaleTimeOptions> {
        return {
            minUnit: this.timePeriod,
            unit: this.timePeriod,
            tooltipFormat: this.getTooltipFormat(),
        };
    }

    getTooltipFormat(): string {
        switch (this.timePeriod) {
            case "day":
                return "y-MM-dd";
            case "week":
                return "'Week' w/y"
            case "month":
                return "MMM y";
            case "year":
                return "y";
        }
    }

    getUrl(path: string) {
        const rootInput = document.getElementById("__root_path__")
        const root = rootInput instanceof HTMLInputElement ? rootInput.value : "";

        return root.replace(/\/$/, "") + "/" + path.replace(/^\//, "");
    }

    async render() {
        this.chart?.destroy();
        this.chart = await this.renderChart();
    }

    reset(event: Event) {
        event.preventDefault();
        [this.startDate, this.endDate] = this.getDefaultDates();
        this.timePeriod = this.canvas.dataset.period as TimePeriod;
        if (this.timePeriodSelect) this.timePeriodSelect.value = this.timePeriod;
        if (this.startInput) this.startInput.valueAsDate = this.startDate;
        if (this.endInput) this.endInput.valueAsDate = this.endDate;

        this.render();
    }

    abstract getDefaultDates(): [Date, Date];

    abstract renderChart(): Promise<Chart>;
}
