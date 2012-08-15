$.fn.zato.stats.top_n.show_hide = function(selectors, show) {
    $.each(selectors, function(idx, selector) {
        var result = $(selector);
        if(show) {
            result.removeClass('hidden').addClass('visible');
        }
        else {
            result.removeClass('visible').addClass('hidden');
        }
    })
};

$.fn.zato.stats.top_n.switch_highlight = function(this_, remove_class, add_class) { 
    var id = $(this_).attr('id');
    id = _.last(_.str.words(id, '-'));
    if(id) {
      $('tr[id*="' +id+'"] > td').removeClass(remove_class).addClass(add_class);
    };
};

$.fn.zato.stats.top_n.data_callback = function(data, status) {

    var side = this['side'];

    var json = $.parseJSON(data.responseText);
    $(String.format('.{0}-loading-tr', side)).hide();
    
    var n_types = ['mean', 'usage'];
    $.each(n_types, function(idx, n_type) {
        $(String.format('#{0}-{1}-tr', side, n_type)).after(json[n_type]);
        $(String.format('#{0}-{1}', side, n_type)).tablesorter();
    });
    
    var show_hide = [String.format('.{0}-csv', side), '#compare_to', String.format('.{0}-date', side)];
    
    $.each(['start', 'stop'], function(idx, time) {
        $(String.format('#{0}-{1}', side, time)).val(json[time]);
        $(String.format('#{0}-{1}-label', side, time)).text(json[time+'_label']);
    });
    
    $.fn.zato.stats.top_n.show_hide([String.format('.{0}-date', side)], true);
    
    /* The right side has never been shown yet so we need to update its start/stop
       parameters even though the shift was on the left one.
    */

    if(json.has_stats) {

        var sparklines_options = {'width':'36px', 'height':'15px', 'lineColor':'#555', 'spotColor':false, 'fillColor':false}    

        $.fn.zato.stats.top_n.show_hide(show_hide, true);

        $(String.format('.{0}-trend', side)).sparkline('html', sparklines_options);
        $(String.format('#{0}-usage-csv', side)).attr('href', json.usage_csv_href);
        $(String.format('#{0}-mean-csv', side)).attr('href', json.mean_csv_href);
        
        $('.stats-table tr').mouseover(function() {
            $.fn.zato.stats.top_n.switch_highlight(this, 'default', 'hover');
        });
                
        $('.stats-table tr').mouseout(function(){
            $.fn.zato.stats.top_n.switch_highlight(this, 'hover', 'default');
       });
        
    }
};

$.fn.zato.stats.top_n.shift = function(side, shift, date_prefix) {
    var data = {};
    
	if(side == 'right') {
		$.fn.zato.stats.top_n.show_hide(['#right-side'], true);
	}
	
	if(!date_prefix) {
		date_prefix = side;
	}
	
	$.each(['csv', 'date'], function(idx, elem) {
		$.fn.zato.stats.top_n.show_hide([String.format('{0}-{1}', side, elem)], false);
	});

	$(String.format('.{0}-loading-tr', side)).show();
	$(String.format('tr[id^="{0}-tr-mean"], tr[id^="{0}-tr-usage"]', side)).empty().remove();
	
	var keys = [String.format('{0}-start', date_prefix), String.format('{0}-stop', date_prefix), 'n', 'cluster_id'];
	
	$.each(keys, function(idx, key) {
		data[key.replace('left-', '').replace('right-', '').replace('custom-', '')] = $('#'+key).val();
	});
	
	data['side'] = side;
	data['shift'] = shift;
    
    $.fn.zato.post('../data/', $.fn.zato.stats.top_n.data_callback, data, 'json', true, {'side': side});
}

$.fn.zato.stats.top_n.show_start_stop_picker = function() {
	var div = $('#custom_date');
	div.prev().text('Choose start/end dates for the right-side statistics'); // prev() is a .ui-dialog-titlebar
	div.dialog('open');
}

$.fn.zato.stats.top_n.change_date = function(side, shift) {
    $('#shift').val('');
    if(side == 'left') {
        $('#page_label').text('Custom set, step one hour')
    }

    $.fn.zato.stats.top_n.shift(side, shift);
};

$.fn.zato.stats.top_n.initial_data = function() {
    var data = {};
    var keys = ['cluster_id', 'left-start', 'left-stop', 'n'];
    var value = null;
    
    $.each(keys, function(idx, key) {
        value = $('#'+key).val();
        data[key.replace('left-', '')] = value;
    });
    
    data['side'] = 'left';
    $.fn.zato.post('../data/', $.fn.zato.stats.top_n.data_callback, data, 'json', true, {'side': 'left'});
};

$.fn.zato.stats.top_n.on_custom_date = function() {
	var custom_date_form_id = '#form-custom_date'
	var custom_date_form = $(custom_date_form_id);
	
	if(custom_date_form.data('bValidator').isValid()) {
		$.fn.zato.stats.top_n.shift('right', '', 'custom');
		$.fn.zato.data_table.cleanup(custom_date_form_id);
		return true;
	}
};

$.fn.zato.stats.top_n.setup_forms = function() {

	$.each(['start', 'stop'], function(ignored, suffix) {
		var field_id = String.format('#custom-{0}', suffix)
		$(field_id).attr('data-bvalidator', 'required');
		$(field_id).attr('data-bvalidator-msg', 'This is a required field');

		$(field_id).datetimepicker();
	});
	
	var custom_date_form_id = '#form-custom_date'
	var custom_date_form = $(custom_date_form_id);
	
	custom_date_form.submit(function(e) {
		e.preventDefault();
		if($.fn.zato.stats.top_n.on_custom_date()) {
			$('#custom_date').dialog('close');
		}
	});
	
	custom_date_form.bValidator();
	
	$('#custom_date').dialog({
		autoOpen: false,
		width: '40em',
		close: function(e, ui) {
			$.fn.zato.data_table.reset_form(custom_date_form_id);
		}
	});
}

$(document).ready(function() {
	$.fn.zato.stats.top_n.setup_forms();
	$.fn.zato.stats.top_n.initial_data();
})
