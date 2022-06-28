// Script para desarrollador

//Función que se ejecuta al inicio de la aplicación

function init() {
    load_init()
    disable_init()
}

function disable_init() {
    $('#div_month_year').hide();
    $('#div_from_to').hide();
    $('#div_day').hide();

    // // por defecto queda marcado el mes actual
    // $("#rb_month").is("checked", true);
}

function load_init() {
    $(document).ready(function () {
        // por mes y año
        $("#rb_month").change(function () {
            if ($("#rb_month").prop("checked")) {
                $('#div_month_year').show();
                $('#div_from_to').hide();
                $('#div_day').hide();

                $("[name='month_in']").attr("required", true);
                $("[name='in_year']").attr("required", true);

                $("[name='in_date_start']").attr("required", false);
                $("[name='in_date_end]").attr("required", false);

                $("[name='in_day]").attr("required", false);
            }
        });

        // por fechas
        $("#rb_dates").change(function () {
            if ($("#rb_dates").prop("checked")) {
                $('#div_from_to').show();
                $('#div_month_year').hide();
                $('#div_day').hide();

                $("[name='month_in']").attr("required", false);
                $("[name='in_year']").attr("required", false);

                let date = new Date();
                $("[name='in_date_start']").attr("required", true);

                $("#in_date_start").val(new Date().toJSON().slice(0, 10));
                $("#in_date_end").val(new Date().toJSON().slice(0, 10));

                $("[name='in_date_end]").attr("required", true);

                $("[name='in_day]").attr("required", false);
            }
        });

        // por dia
        $("#rb_day").change(function () {
            if ($("#rb_day").prop("checked")) {
                $('#div_from_to').hide();
                $('#div_month_year').hide();
                $('#div_day').show();

                $("[name='month_in']").attr("required", false);
                $("[name='in_year']").attr("required", false);

                $("[name='in_date_start']").attr("required", false);
                $("[name='in_date_end]").attr("required", false);

                $("[name='in_day]").attr("required", false);
                $("#in_day").val(new Date().toJSON().slice(0, 10));

            }
        });

        // todo
        $("#rb_all").change(function () {
            if ($("#rb_all").prop("checked")) {
                $('#div_from_to').hide();
                $('#div_month_year').hide();
                $('#div_day').hide();

                $("[name='month_in']").attr("required", false);
                $("[name='in_year']").attr("required", false);

                $("[name='in_date_start']").attr("required", false);
                $("[name='in_date_end]").attr("required", false);

                $("[name='in_day]").attr("required", false);
            }
        });


    });
}

// Una vez que se cargan todos los métodos se ejecuta la función init()
init();