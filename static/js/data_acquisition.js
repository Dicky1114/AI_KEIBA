$(function() {
  $(document).on('click', '.login_button2', function() {
    console.log("hello");
    $('.server_message').empty();
    $.ajax({
    url: "{% url 'app_folder:test' %}",
        type: 'POST',
        dataType: 'text',
        headers: { 'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')  },
        data: {
          'test_message': "message_detail"
        }
      }).done(function(data) {
              console.log(data);
              $('.server_message').append(data);
        }).fail(function(data) {

        });
  });

});  