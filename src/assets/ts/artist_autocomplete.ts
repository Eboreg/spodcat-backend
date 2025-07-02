{
    function initArtistAutocomplete(selector: any) {
        const $ = django.jQuery;
        const select2 = $(selector).find(".field-artists .admin-autocomplete").not("[name*=__prefix__]");

        select2.each(function(i, element) {
            $(element).select2({
                ajax: {
                    data: (params) => {
                        return {
                            term: params.term,
                            page: params.page,
                            app_label: element.dataset.appLabel,
                            model_name: element.dataset.modelName,
                            field_name: element.dataset.fieldName,
                        };
                    },
                },
                tags: true,
                createTag: function(params) {
                    if (typeof params.term != "string") return null;
                    const term = params.term.trim();
                    if (term == "") return null;

                    return {
                        id: `NEW--${term}`,
                        text: term,
                        newTag: true,
                    };
                },
            })
        })
    }

    $(function() {
        initArtistAutocomplete(document);
    });

    document.addEventListener("formset:added", (event) => {
        initArtistAutocomplete(event.target);
    });
}
