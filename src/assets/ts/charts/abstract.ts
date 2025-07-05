import { Chart } from "chart.js";
import { getContext } from "./utils";


export abstract class AbstractGraph {
    canvas: HTMLCanvasElement;
    chart: Chart | undefined;

    constructor(canvas: HTMLCanvasElement) {
        this.canvas = canvas;
    }

    formatDuration(totalSeconds: number) {
        const hours = Math.floor(totalSeconds / 60 / 60);
        const minutes = Math.floor((totalSeconds / 60) % 60);
        const seconds = Math.floor(totalSeconds % 60);

        if (hours) return `${hours}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
        return `${minutes}:${String(seconds).padStart(2, "0")}`;
    }

    getUrl(path: string) {
        const root: string = getContext().rootPath || "";

        return root.replace(/\/$/, "") + "/" + path.replace(/^\//, "");
    }
}


export abstract class AbstractEpisodePlaysGraph extends AbstractGraph {
    async render(startDate: Date, endDate: Date) {
        this.chart?.destroy();
        this.chart = await this.renderChart(startDate, endDate);
    }

    abstract renderChart(startDate: Date, endDate: Date): Promise<Chart>;
}
