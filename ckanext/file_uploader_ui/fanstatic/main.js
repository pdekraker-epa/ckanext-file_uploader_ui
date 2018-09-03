/* global $, window */

$(function () {
    'use strict';
    let firstAdd = false;
    $('#fileupload').fileupload({
        url: '/file_uploader_ui/upload'
    }).bind('fileuploadadd', function(e, data) {
        if (!firstAdd) {
            firstAdd = true;
            $('aside.secondary').removeClass('col-sm-3').addClass('col-sm-9');
            $('div.primary').hide();
            $('aside.secondary section:first').hide();
            $('#fileupload button.start').removeClass('hidden');
            $('#fileupload button.cancel').removeClass('hidden');
            $(this).removeClass('fileupload-processing');
        }
    });
});
