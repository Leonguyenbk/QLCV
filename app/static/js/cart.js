function addToCart(event, id, name, price) {
  event.preventDefault(); // Ngăn reload trang

  fetch('/api/add-cart', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      id: id,
      name: name,
      price: price
    })
  }).then(function(res) {
    return res.json()
  }).then(function(data){
    console.info(data)

    let counter = document.getElementById('cartCounter')
    counter.innerText = data.total_quantity
  }).catch(function(err) {
    console.error(err)
  })
}

function pay() {
  if (confirm('Bạn chắc chắn muốn thanh toán không?')==true){
      fetch('/api/pay', {
      method: 'POST',
      
    }).then(function(res) {
        return res.json()
    }).then(function(data){
        if (data.code == 200)
          location.reload()
    }).catch(function(err) {
      console.error(err)
    })
  }
}