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
    
    $(".anchor").click(function(e){
        e.preventDefault()
        var href=$(e.target).attr("data-href")
        window.location.href=href
    })
})

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