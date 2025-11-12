const openModal = (id) => {
  const modal = document.getElementById(id);
  if (modal) {
    modal.classList.add("is-visible");
    modal.setAttribute("aria-hidden", "false");
  }
};

const closeModal = (id) => {
  if (id === "all") {
    document.querySelectorAll(".modal").forEach((modal) => {
      modal.classList.remove("is-visible");
      modal.setAttribute("aria-hidden", "true");
    });
    return;
  }
  const modal = document.getElementById(id);
  if (modal) {
    modal.classList.remove("is-visible");
    modal.setAttribute("aria-hidden", "true");
  }
};

document.querySelectorAll("[data-open]").forEach((btn) => {
  btn.addEventListener("click", (event) => {
    event.stopPropagation();
    const target = btn.dataset.open;
    if (target) {
      openModal(target);
    }
  });
});

document.querySelectorAll("[data-close]").forEach((btn) => {
  btn.addEventListener("click", (event) => {
    event.stopPropagation();
    const target = btn.dataset.close || "all";
    closeModal(target);
  });
});

document.querySelectorAll(".modal").forEach((modal) => {
  modal.addEventListener("click", (event) => {
    if (event.target === modal) {
      modal.classList.remove("is-visible");
      modal.setAttribute("aria-hidden", "true");
    }
  });
});

window.addEventListener("keyup", (event) => {
  if (event.key === "Escape") {
    closeModal("all");
  }
});

// 主界面中的路由行双击打开编辑弹窗
document.querySelectorAll("tbody tr").forEach((row) => {
  row.addEventListener("dblclick", () => openModal("modal-route"));
});

// 结果列中的状态点击打开验证弹窗
document.querySelectorAll("td .status").forEach((status) => {
  status.addEventListener("click", (event) => {
    event.stopPropagation();
    openModal("modal-verify");
  });
});

// 状态栏快捷入口
const statusBar = document.querySelector(".status-bar");
if (statusBar) {
  statusBar.addEventListener("click", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    if (target.matches(".status-wireguard") || target.closest(".status-wireguard")) {
      openModal("modal-settings");
    } else if (target.matches(".status-default") || target.closest(".status-default")) {
      openModal("modal-interface");
    } else if (target.matches(".status-apply") || target.closest(".status-apply")) {
      openModal("modal-snapshot");
    }
  });
}

