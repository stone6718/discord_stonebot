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

function add(userId) {
    swal({
        text: "추가할 금액을 입력해주세요.",
        content: "input",
        buttons: {
            cancel: "취소",
            confirm: {
                text: "확인"
            }
        }
    }).then(answer => {
        if (!answer) return;
        answer = parseInt(answer);
        if (isNaN(answer)) {
            return swal("정수만 입력해주세요.");
        }

        fetch(document.location.href, {
            headers: {
                "content-type": "application/json"
            },
            method: "POST",
            body: JSON.stringify({
                type: "add",
                amount: answer,
                userId
            })
        }).then(async res => {
            const body = await res.json();
            if (body) swal("저장이 완료되었습니다.").then(() => document.location = document.location);
        });
    });
}

function set(userId) {
    swal({
        text: "설정할 금액을 입력해주세요.",
        content: "input",
        buttons: {
            cancel: "취소",
            confirm: {
                text: "확인"
            }
        }
    }).then(answer => {
        if (!answer) return;
        answer = parseInt(answer);
        if (isNaN(answer)) {
            return swal("정수만 입력해주세요.");
        }

        fetch(document.location.href, {
            headers: {
                "content-type": "application/json"
            },
            method: "POST",
            body: JSON.stringify({
                type: "set",
                amount: answer,
                userId
            })
        }).then(async res => {
            const body = await res.json();
            if (body) swal("저장이 완료되었습니다.").then(() => document.location = document.location);
        });
    });
}

function disable(userId, disabled) {
    fetch(document.location.href, {
            headers: {
                "content-type": "application/json"
            },
            method: "POST",
            body: JSON.stringify({
                type: "disable",
                disabled: disabled,
                userId
            })
        }).then(async res => {
            const body = await res.json();
            if (body) swal("저장이 완료되었습니다.").then(() => document.location = document.location);
        });
}

function remove(userId) {
    swal({
        title: "정말로 데이터를 삭제하시겠습니까?",
        text: "삭제된 데이터는 복구할 수 없습니다.",
        buttons: {
            cancel: "취소",
            confirm: {
                text: "확인"
            }
        }
    }).then(answer => {
        if (!answer) return;
        fetch(document.location.href, {
            headers: {
                "content-type": "application/json"
            },
            method: "POST",
            body: JSON.stringify({
                type: "remove",
                userId
            })
        }).then(async res => {
            const body = await res.json();
            if (body) swal("데이터가 삭제되었습니다.").then(() => document.location = document.location);
        });
    });
}

function removeGuild() {
    swal({
        title: "정말로 서버 데이터베이스를 삭제하시겠습니까?",
        text: "삭제된 데이터는 복구할 수 없습니다.",
        buttons: {
            cancel: "취소",
            confirm: {
                text: "확인"
            }
        }
    }).then(answer => {
        if (!answer) return;
        fetch(document.location.href, {
            headers: {
                "content-type": "application/json"
            },
            method: "POST",
            body: JSON.stringify({
                type: "remove_guild"
            })
        }).then(async res => {
            const body = await res.json();
            if (body) swal("서버 데이터베이스가 삭제되었습니다.").then(() => document.location = "/");
            else swal("오류가 발생하였습니다.");
        });
    });
}