window.addEventListener("load", function() {
    // Redirect to /mobile if screen width is less than 768px
    if (window.innerWidth < 768) {
        window.location.href = "/mobile";
    }
});

window.addEventListener("resize", function() {
    if (window.innerWidth < 768) {
        window.location.href = "/mobile";
    }
});