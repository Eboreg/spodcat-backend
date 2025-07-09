declare global {
    const django: {
        jQuery: JQueryStatic;
    };
}

export interface GraphApiResponse {
    datasets: {
        label: string;
        data: {
            x: number;
            y: number;
        }[];
    }[];
}

export type TimePeriod = "day" | "week" | "month" | "year";
