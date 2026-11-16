// <!-- Utility functions -->

// Check if an item exists in item_list
function itemExists(item_list, item_id) {
    var extsts = false;
    // Use of ES5 deliberate since a lot of users might a have old browsers
    for (var i = 0; i < item_list.length; i++) {
        if (item_list[i].id == item_id) {
            exists = true
            break;
        }
    }
    return extsts
}

function getIndex(item_list, item_id) {
    var index = null;
    for (var i = 0; i < item_list.length; i++) {
        if (item_list[i].id == item_id) {
            index = i
            break;
        }
    }
    return index
}

// Get object from a list (item_list) of id item_id
function getObject(item_list, item_id) {
    var object = {}
    for (var i = 0; i < item_list.length; i++) {
        if (item_list[i].id == item_id) {
            object = item_list[i]
            break;
        }
    }
    return object
} // <!-- Utility functions end -->

// <!-- Script for filling table with  selected items -->
function makeRow(item_id, item_list) {
    var item = getObject(item_list, item_id)
    var price = item.price
    var name = item.name
    var quantity = item.quantity
    var amount = item.amount
    var unit = item.unit

    return `
			<tr id='row-${item_id}'>
				<td>${name}</td>
				<td>${price}/${unit}</td>		
			</tr>	
		`
    // <tr id='row-${item_id}'>
    // 		<td>${name}</td>
    // 		<td>${price}/${unit}</td>
    // 		<td class="d-flex justify-content-center">
    // 			<div class="num-block skin-2">
    // 			<div class="num-in">
    // 				<span class="minus dis"></span>
    // 				<input type="text" id='quantity-${item_id}' data-id='${item_id}' class="in-num" value="${quantity}">
    // 				<span class="plus"></span>
    // 			</div>
    // 			</div> 
    // 		</td>
    // 		<td id='amount-${item_id}'>${amount}</td>
            
    // 	</tr>	
}


/*  Add Image design  
<td class="d-flex align-items-center justify-content-center flex-nowrap">
					<div class="image-upload me-1">
						<label for="file-input">
							<p class="mb-0 btn btn-primary-custom btn-sm">
								<i class="fa fa-file-image-o" aria-hidden="true"></i>
							</p>
						</label>
		
						<input id="file-input" type="file" style="display: none;" />
					</div>	
					<a href="#" class="btn btn-sm btn-primary-custom">
						<i class="fa fa-camera" aria-hidden="true"></i>
					</a>	
				</td>*/
// <!-- Script for filling table with  selected items end -->

// <!-- Script for adding/removing items -->
let item_count = 0;

$(document).ready(function() {
    var item_list = JSON.parse(window.localStorage.getItem('item_list'));
    try {
        item_count = item_list.length
    } catch (error) {
        item_count = 0
    }
})

function addItem(item_id) {
    // add current item to item_list

    var item_object = {
        'id': item_id,
        'name': $(`#item-name-${item_id}`).text(),
        'price': parseFloat($(`#item-price-${item_id}`).val()).toFixed(2),
        'quantity': 1,
        'amount': parseFloat($(`#item-price-${item_id}`).val()).toFixed(2),
        'unit': $(`#item-unit-${item_id}`).text()
    }

    // get item_list from localStorage
    var item_list = JSON.parse(window.localStorage.getItem('item_list'));

    if (item_list) {
        // do nothing
    } else {
        // make item_list empty array
        item_list = []
    }

    item_list.push(item_object)

    // store item_list in localstorage
    window.localStorage.setItem('item_list', JSON.stringify(item_list))

    // Change Item Count
    item_count += 1;

    // Add in table
    $('#item-table').append(makeRow(item_id, item_list))

    // hide empty-row
    $('#empty-row').hide()

    // enable confirm-btn
    $("#confirm-btn").addClass('anchor')
    $("#confirm-btn").prop('disabled', false)
}

function removeItem(item_id) {
    // remove item from item_list

    // get item_list from localstorage
    var item_list = JSON.parse(window.localStorage.getItem('item_list'));

    // get index
    var index = getIndex(item_list, item_id)

    // remove from item_list
    item_list.splice(index, 1)

    // store item_list in localstorge
    window.localStorage.setItem('item_list', JSON.stringify(item_list))

    // Change item_count
    item_count -= 1

    // remove row from table
    $(`#row-${item_id}`).remove()

    // show empty-row if item_count == 0
    if (item_count == 0) {
        $('#empty-row').show()
        $("#confirm-btn").removeClass('anchor')
        $("#confirm-btn").prop('disabled', true)
    }
}

// <!-- Script for adding/removing items end -->

// <!-- Script for selecting items -->
function ItemClick(item_id) {
    var item = $(`#check-${item_id}`);

    if (item.is(":checked")) {
        addItem(item_id);
    } else {
        removeItem(item_id)
    }
}

// <!-- Script for selecting items end -->

// <!-- Script for changing amount and keeping quantity atleast 1 -->
$(document).on('change', '.in-num', function(e) {
    var input = $(e.target)
    var item_id = input.attr('data-id') // Get id

    // get quantity
    var quantity = new Number()
    try {
        quantity = parseFloat(input.val()).toFixed(2)
        if (quantity < 1) {
            input.val(1)
        }
    } catch (error) {
        quantity = 1
        input.val(1)
    }

    // get price of item and set amount
    var price = parseFloat($(`#item-price-${item_id}`).val()).toFixed(2)
    var amount = (price * quantity).toFixed(2)
    $(`#amount-${item_id}`).text(amount) // display amount

    // Get item_list from local storage
    var item_list = JSON.parse(window.localStorage.getItem('item_list'))

    // Get index
    var index = getIndex(item_list, item_id)

    // Set new values
    item_list[index].quantity = quantity
    item_list[index].amount = amount

    // store item_list in localstorge
    window.localStorage.setItem('item_list', JSON.stringify(item_list))
})

// <!-- Script for changing amount and keeping quantity atleast 1 end -->


// <!-- Script for fi -->