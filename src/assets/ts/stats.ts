import {
    BarController,
    BarElement,
    Chart,
    Colors,
    Filler,
    Legend,
    LinearScale,
    LineController,
    LineElement,
    PointElement,
    TimeScale,
    Title,
    Tooltip,
} from "chart.js";
import "chartjs-adapter-date-fns";
import UniqueIpsGraph from "./graphs/UniqueIpsGraph";
import EpisodePlaysGraph from "./graphs/EpisodePlaysGraph";

function initChartJs() {
    Chart.register(
        BarController,
        BarElement,
        Colors,
        Filler,
        Legend,
        LinearScale,
        LineController,
        LineElement,
        PointElement,
        TimeScale,
        Title,
        Tooltip,
    );

    Chart.defaults.color = "#eeeeee";
    Chart.defaults.borderColor = "#bb886644";
    Chart.defaults.datasets.line.fill = "start";
    Chart.defaults.animation = false;
    Chart.defaults.datasets.line.normalized = true;
    Chart.defaults.datasets.line.tension = 0;
    Chart.defaults.scales.linear.ticks.maxRotation = 0;
    Chart.defaults.scales.time.time.isoWeekday = true;
    Chart.defaults.scales.time.time.tooltipFormat = "y-MM-dd";
    Chart.defaults.scales.time.time.displayFormats = {
        month: "MMM yyyy",
        week: "w/y",
        year: "y",
        day: "y-MM-dd",
    };
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

function initStatsTables() {
    document.querySelectorAll(".stats-table.collapsible").forEach((table) => {
        table.querySelector(".expand-link a")?.addEventListener("click", (event) => {
            event.preventDefault();
            table.classList.remove("collapsed");
        });

        table.querySelector(".collapse-link a")?.addEventListener("click", (event) => {
            event.preventDefault();
            table.classList.add("collapsed");
        });
    });
}

function initUniqueIpsGraph(selector: string, graphType: string) {
    const canvas = document.querySelector(selector);

    if (canvas instanceof HTMLCanvasElement) {
        const graph = new UniqueIpsGraph(canvas, graphType);
        graph.render();
    }
}

initChartJs();

addEventListener("DOMContentLoaded", () => {
    const startInput = document.querySelector("input[name=daily-plays-start-date]");
    const endInput = document.querySelector("input[name=daily-plays-end-date]");

    initStatsTables();
    initUniqueIpsGraph(".unique-ips-graph", "unique-ips");
    initUniqueIpsGraph(".rss-unique-ips-graph", "rss-unique-ips");

    document.querySelectorAll(".episode-plays-graph").forEach((element) => {
        if (element instanceof HTMLCanvasElement) {
            const graph = new EpisodePlaysGraph(element, startInput, endInput);
            graph.render();
        }
    });
});
