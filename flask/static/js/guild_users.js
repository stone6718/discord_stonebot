async function logout() {
    await fetch("/logout", { method: "POST" });
    document.location = "/login";
}

function navigate(pageName) {
    const path = document.location.pathname.split("/");
    path.pop();
    path.push(pageName);
    document.location = path.join("/");
}