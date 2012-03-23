jQuery(document).ready(function(){
	var busy = false;
	if (jQuery('#export-running').is(":visible")) {
		busy = true;
	}
	var static_deployment_form = jQuery('#static-deployment-form');
	
    setInterval( function() {
		if (static_deployment_form.length) {
			jQuery.ajax({
				url: 'check_mutex',
				dataType: "text",
				success: function(data){
					if (data == 'True') {
						jQuery('#export-running').hide();
						if (busy) {
							window.location = '@@staticdeployment-controlpanel';
						}
						busy = false;
					}
					else {
						busy = true;
					}
				},
			})
		}
    }, 8000);

	jQuery('#static-deployment-form').ajaxForm({ 
	  resetForm: true,
	  beforeSubmit: function(data, $form){
		
		var names = jQuery.map(data, function(i){
			return i.name;
		});
		var save = jQuery.inArray("form.actions.save", names);
		var cancel = jQuery.inArray("form.actions.cancel", names);
		var choice = jQuery.inArray("form.section_choice", names);
		var deployment = jQuery.inArray("form.deployment", names);
		
		var queue = true;
		var future_queue = false;
		var queue_date = jQuery.inArray("form.queue_date", names);
		if (queue_date > 0){
			queue_date = new Date(data[queue_date].value);
			now = new Date();
			var past = now.setMinutes(now.getMinutes() - 5);
			var date_field = jQuery("#form\\.queue_date");
			if (queue_date < past){
				queue = false;
				date_field.parent().parent().addClass('error');
				if (date_field.parent().children('.errorText').length == 0){
					date_field.parent().prepend('<div class="errorText">Data z przeszłości</div>');
				} 
			}
			else{
				if (queue_date > new Date()){
					future_queue = true;
				}
				queue = true;
				date_field.parent().parent().removeClass('error');
				date_field.parent().children('.errorText').remove();
			}
		}
		
		if (cancel>=0){
			window.location = '@@staticdeployment-controlpanel';
		}
		
		if (save>=0){
			if (!busy) {
				if (choice>=0 && deployment>=0 && queue && !future_queue){
				  	$form.resetForm();
					busy = true;
					$form.addClass('running');
					jQuery('#export-params-error').hide();
			    	jQuery('#export-running').show();
				}
				else{
					$form.removeClass('running');
					jQuery('#export-running').hide();
					jQuery('#export-running-error').hide();
					if (choice < 0 || deployment < 0 || !queue) {
						jQuery('#export-params-error').show();
					}
					else{
						jQuery('#export-params-error').hide();
						jQuery('#export-queued-info').show();
					}
				}
			}
			else {
				jQuery('#export-running-error').show();
				scroll(0,0);
			}
		}},
    });
});