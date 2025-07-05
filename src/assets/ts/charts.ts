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
import type { AbstractEpisodePlaysGraph } from "./charts/abstract";
import { getContext, getEarliestDate, getPlayTimeEndDate, getPlayTimeStartDate } from "./charts/utils";
import UniqueIpsGraph from "./charts/UniqueIpsGraph";
import PodcastEpisodePlaysGraph from "./charts/PodcastEpisodePlaysGraph";
import EpisodePlaysGraph from "./charts/EpisodePlaysGraph";

const playTimeGraphs: AbstractEpisodePlaysGraph[] = [];

function initChartJs() {
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
}

function initPlayTimeFields() {
    const startElem = document.querySelector("input[name=daily-plays-start-date]");
    const endElem = document.querySelector("input[name=daily-plays-end-date]");
    const earliestDate = getEarliestDate();
    const endDate = getPlayTimeEndDate();
    const startDate = getPlayTimeStartDate();

    if (startElem instanceof HTMLInputElement && endElem instanceof HTMLInputElement) {
        startElem.valueAsDate = startDate;
        endElem.valueAsDate = endDate;
        endElem.min = startElem.value;
        endElem.max = endDate.toISOString().slice(0, 10);
        startElem.max = endElem.value;
        startElem.min = earliestDate.toISOString().slice(0, 10);

        const renderGraphs = () => {
            for (const graph of playTimeGraphs) {
                graph.render(startElem.valueAsDate, endElem.valueAsDate);
            }
        };

        startElem.addEventListener("change", async () => {
            renderGraphs();
            endElem.min = startElem.value;
        });
        endElem.addEventListener("change", async () => {
            renderGraphs();
            startElem.max = endElem.value;
        });
    }
}

initChartJs();

addEventListener("DOMContentLoaded", () => {
    initPlayTimeFields();

    const podcastPlayTimeCanvas = document.getElementById("podcast-episode-plays-chart");
    const uniqueIpsCanvas = document.getElementById("unique-ips-chart");
    const rssUniqueIpsCanvas = document.getElementById("rss-unique-ips-chart");
    const context = getContext();

    if (uniqueIpsCanvas instanceof HTMLCanvasElement) {
        const graph = new UniqueIpsGraph(uniqueIpsCanvas, "unique-ips", context.strings.uniqueIpsTitle);

        graph.render();
    }

    if (rssUniqueIpsCanvas instanceof HTMLCanvasElement) {
        const graph = new UniqueIpsGraph(rssUniqueIpsCanvas, "rss-unique-ips", context.strings.rssUniqueIpsTitle);

        graph.render();
    }

    if (podcastPlayTimeCanvas instanceof HTMLCanvasElement) {
        const graph = new PodcastEpisodePlaysGraph(podcastPlayTimeCanvas);

        playTimeGraphs.push(graph);
        graph.render(getPlayTimeStartDate(), getPlayTimeEndDate());
    }

    document.querySelectorAll(".episode-plays-chart").forEach((element) => {
        if (element instanceof HTMLCanvasElement && element.dataset.podcastSlug) {
            const graph = new EpisodePlaysGraph(element, element.dataset.podcastSlug, element.dataset.podcastName);

            playTimeGraphs.push(graph);
            graph.render(getPlayTimeStartDate(), getPlayTimeEndDate());
        }
    });
});
