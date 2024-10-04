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

function toggle(commandName, enabled) {
    fetch(document.location.href, {
        headers: {
            "content-type": "application/json"
        },
        method: "POST",
        body: JSON.stringify({
            command: commandName,
            enabled
        })
    }).then(async res => {
        const body = await res.json();
        if (body) swal("저장이 완료되었습니다.").then(() => document.location = document.location);
        console.log(body);
    });
}