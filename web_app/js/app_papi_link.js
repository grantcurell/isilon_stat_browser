var cluster_ip = null
var clicked_link = null

$(document).ready(function () {
  $('.papi_demo').click(papi_link_clicked)
  $('#modal_cluster_save').click(save_cluster_ip)
  $('#modal_cluster').on('shown.bs.modal', function () {$('#text_cluster').focus()})
  cluster_ip = keyDict['cluster']['host']
  if (cluster_ip != null) {
    // Populate PAPI links if IP is known
    update_papi_links(keyDict['cluster']['host'])
  }
});

function papi_link_clicked() {
  if (cluster_ip == null) {
    clicked_link = $(this)
    $('#modal_cluster').modal()
    return false
  }
}

function set_cluster_ip() {
  clicked_link = null
  $('#modal_cluster').modal()
}

function save_cluster_ip() {
  cluster_ip = $('#text_cluster').val()
  $('#modal_cluster').modal('hide')
  update_papi_links(cluster_ip)
  $('#button_cluster_ip').show()
  if (clicked_link != null) {
    window.open($(clicked_link).attr('href'), '_blank')
  }
}

function update_papi_links() {
  $('.papi_demo_current').each(update_papi_link, ['current'])
  $('.papi_demo_history').each(update_papi_link, ['history'])

}

function update_papi_link(endpoint) {
  key = $(this).parentsUntil('.key_main').find('span.key-name').text()
  link = papi_stat_link(key, endpoint, 1)
  $(this).attr('href', link)
  $(this).text(link)
}


function antisquash_key(key) {
  // If a key ends in .N, convert the N to 1
  if (key.endsWith('.N')) {
    key =  key.replace(/\.N$/, '.1')
  }
  return key
}

function papi_stat_link(key, endpoint, papi_vers) {
  key = antisquash_key(key)
  const uri = '/platform/' + papi_vers + '/statistics/' + endpoint;
  const pathParam = encodeURIComponent(uri);
  const keyParam = encodeURIComponent(key);
  const link = '/papi?path=' + pathParam + '&key=' + keyParam;
  return link;
}
