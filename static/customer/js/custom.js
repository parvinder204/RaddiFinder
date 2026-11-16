// New js scripts
$(document).ready(function () {
    $('.number-only').keypress(function (e) {
        dec_bool = $(e.target).get(0).hasAttribute('decimal')
        if (e.which != 8 && e.which != 0 && (e.which < 48 || e.which > 57)) {
            if(dec_bool && e.which === 46){
                var val = $(this).val()
                for(var i = 0; i < val.length; i++){
                    if(val[i] == "."){
                        return false
                    }
                }
                
            }else{
                return false
            }
        }
    })

    $('.length-limit').keypress(function (e) {
        var data_length = $(e.target).attr('maxlength')
        if (data_length) {
            data_length = parseInt(data_length)
            if ($(e.target).val().length < data_length) {
                console.log(data_length);
                //do nothing
            } else {
                return false
            }
        }
    })

    $(document).on('click', '.anchor', function (e) {
        e.preventDefault()
        var href = $(e.target).attr("data-href")
        window.location.href = href
    })

    $(".defunct-anchor").click(function (e) {
        e.preventDefault()
    })
})

//  New js scripts end

$(document).ready(function () {
    $(".loader").delay(500).fadeOut("slow");
})
$(document).ready(function () {

    var navListItems = $('div.setup-panel div a'),
        allWells = $('.setup-content'),
        allt_des = $('.t_des'),
        allNextBtn = $('.nextBtn');

    allWells.hide();

    navListItems.click(function (e) {
        
            e.preventDefault();
            var $target = $($(this).attr('href')),
                $t_des = $($(this).attr('href')+"_des"),
                page_title = $($(this).attr('href')+"_des").attr('t_title'),
                $item = $(this);

            if (!$item.hasClass('disabled')) {
                navListItems.removeClass('btn-primary-custom').addClass('btn-default');
                $item.addClass('btn-primary-custom');
                allWells.hide();
                allt_des.hide();
                allt_des.hide();
                $t_des.show();
                $('#page_title').html(page_title);
                $target.show();

                $target.find('input:eq(0)').focus();
            }
    });

    allNextBtn.click(function () {
        if($(this).attr('lock') == "true")
        {
            $('#sel_itm_prompt').show()
            $('#sel_itm_prompt').attr('tabindex', 0).focus();
        }
        else
        {
            $('#sel_itm_prompt').hide()
            var curStep = $(this).closest(".setup-content"),
                curStepBtn = curStep.attr("id"),
                nextStepWizard = $('div.setup-panel div a[href="#' + curStepBtn + '"]').parent().next().children("a"),
                curInputs = curStep.find("input[type='text'],input[type='url'], textarea, select"),
                isValid = true;

            $(".form-group").removeClass("has-error");
            for (var i = 0; i < curInputs.length; i++) {
                if (!curInputs[i].validity.valid) {
                    isValid = false;
                    $(curInputs[i]).closest(".form-group").addClass("has-error");
                    check_button()
                }
            }
        }

        if (isValid)
            nextStepWizard.removeAttr('disabled').trigger('click');
    });

    $('div.setup-panel div a.btn-primary-custom').trigger('click');
});

function readURL(input) {
    if (input.files && input.files[0]) {
        var reader = new FileReader();
        reader.onload = function (e) {
            $('#imagePreview').css('background-image', 'url(' + e.target.result + ')');
            $('#imagePreview').hide();
            $('#imagePreview').fadeIn(650);
        }
        reader.readAsDataURL(input.files[0]);
    }
}
$("#imageUpload").change(function () {
    readURL(this);
});

/////////////////// product +/-
$(document).ready(function () {
    $(document).on('click', '.num-in span', function () {
        var $input = $(this).parents('.num-block').find('input.in-num');
        if ($(this).hasClass('minus')) {
            var count = parseFloat($input.val()) - 1;
            count = count < 1 ? 1 : count;
            if (count < 2) {
                $(this).addClass('dis');
            }
            else {
                $(this).removeClass('dis');
            }
            $input.val(count);
        }
        else {
            var count = parseFloat($input.val()) + 1
            $input.val(count);
            if (count > 1) {
                $(this).parents('.num-block').find(('.minus')).removeClass('dis');
            }
        }

        $input.change();
        return false;
    })
});
// product +/-

// navbar active

$(document).ready(function(){
    $(".navbar-a").each(function () {
        var e = window.location.href.split(/[?#]/)[0];
        this.href == e &&
            ($(this).addClass("footer-active"),
                n(this).parent().addClass("footer-active"),
                n(this).parent().parent().addClass("footer-active"),
                n(this).parent().parent().parent().addClass("footer-active"),
                n(this).parent().parent().parent().parent().addClass("footer-active"),
                n(this).parent().parent().parent().parent().parent().addClass("footer-active"),
                n(this).parent().parent().parent().parent().parent().parent().addClass("footer-active"));
    })
})

$('.showpass').click(function () {
    var id = $(this).attr('data-id')
    var x= $(`#${id}`)
    if (x.get(0).type === "password") {
        x.get(0).type = "text";
    } else {
        x.get(0).type = "password";
    }
})

$(document).ready(function () {
    $('.p_items').click(function (e) {
        
        a = $('input[type=checkbox]:checked.p_items')
        
        if (a.length > 0)
        {
            console.log("---------------gate opened")
            $('.uatc').removeClass('disabled')
            $('#push_it').attr('lock', 'false')
            $('#sel_itm_prompt').hide()
        }
        else
        {
            console.error("---------------", a.length)
            $('.uatc').addClass('disabled')
            $('#push_it').attr('lock', 'true')
            console.log("---------------gate closed")
        }
    })
})
