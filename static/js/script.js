document.addEventListener("DOMContentLoaded", function () {
    var flashes = document.querySelectorAll(".flash");

    for (var i = 0; i < flashes.length; i++) {
        (function (el) {
            setTimeout(function () {
                el.style.opacity = "0";
                el.style.transition = "opacity .4s";
                setTimeout(function () {
                    if (el.parentNode) {
                        el.parentNode.removeChild(el);
                    }
                }, 450);
            }, 3500);
        })(flashes[i]);
    }
});
