declare global {
    const django: {
        jQuery: JQueryStatic;
    };
}

export interface ChartApiResponse {
    datasets: {
        label: string;
        data: {
            x: number;
            y: number;
        }[];
    }[];
}
