// global variables
const sortStates = {
  balances: { field: "balance-usd-value", order: "desc" },
};
var hideSmallBalances = false;
var showAllBalanceItems = false;
// global variables

var start = function () {
  // global variables from wallet_search template

  attachSortingEventListeners();
  if (walletDataStatus === "ready") {
    markSmallBalances();
  }

  const messageHandlers = {
    balances: handleBalancesMessage,
    transactions: handleTransactionsMessage,
    transactions_details: handleTransactionDetailsMessage,
    current_token_prices: handleCurrentTokenPricesMessage,
    finalized_usd_prices: handleFinalizedUsdPricesMessage,
    historic_balances_p_l: handleHistoricBalancesPLMessage,
    tokens_and_wallet_p_l_info: handleTokensAndWalletPLMessage,
    suspicious_data: handleSuspiciousDataMessage,
    update_available: handleUpdateAvailableMessage,
  };
  // establish channels connection
  var es = new ReconnectingEventSource("/events/");

  es.onopen = function () {
    console.log("connected");
  };
  es.onerror = function () {
    console.log("connection error");
  };
  es.addEventListener(
    "stream-reset",
    function (e) {
      e = JSON.parse(e.data);
      console.log("stream reset: " + JSON.stringify(e.channels));
    },
    false
  );
  es.addEventListener(
    "stream-error",
    function (e) {
      // hard stop
      es.close();
      e = JSON.parse(e.data);
      console.log("stream error: " + e.condition + ": " + e.text);
    },
    false
  );
  es.addEventListener(
    "message",
    function (e) {
      let resp = JSON.parse(e.data);
      // console.log(resp);
      Object.keys(resp).forEach((data_info) => {
        console.log(data_info);

        const handler = messageHandlers[data_info];

        if (handler) {
          handler(resp[data_info]);
        } else {
          console.log("No handler for this type ", data_info);
        }
      });
    },
    false
  );

  function handleBalancesMessage(data) {
    // parses the balances object sent via channels and generates the HTML to display them
    function createBalanceEntry(hash, tdata, extraClass) {
      let html = "";
      html += `
      <div class="${extraClass} balance-container" id="balance-${hash}">
        <div class="balance-token-container">

           <img src="" alt="" class="balance-token-icon">
          
          <div class="balance-token-symbol">${tdata.tokenSymbol}</div>
        </div>
        <span class="balance-token-balance">${tdata.balance}</span>
        <span class="balance-token-last-checked-price-usd"></span> 
        <span class="balance-usd-value"></span>
        <span class="balance-token-p-l"></span>
      </div>
    `;
      return html;
    }

    let balanceContainerDiv = document.getElementById(
      "balance-outer-container"
    );

    Object.entries(data).forEach(([hash, tdata], index) => {
      const extraClass = index > 9 ? "hidden to-be-hidden" : "";

      newHtml = createBalanceEntry(hash, tdata, extraClass);

      balanceContainerDiv.innerHTML += newHtml;
    });
  }

  function handleTransactionsMessage(data) {
    // parses the transactions object sent via channels and generates HTML to display them
    console.log("handleTransactionsMessage");

    function createTransactionsEntry(hash, transaction_info) {
      let html = "";
      ts = new Date(transaction_info.timeStamp * 1000).toLocaleString();
      sent_data = transaction_info.sent;
      html += `<div id="transaction-${hash}" class="transaction-container">`;

      // placeholder for the timestamp
      html += `<span class="transaction-timestamp">${ts}</span>`;

      // conditionally append HTML for sent amount if it exists
      if (transaction_info.sent) {
        html += `
        <div>
          <span class="transaction-sent-amount">-${
            Object.values(transaction_info.sent)[0].final_amount
          }</span>
          ${Object.values(transaction_info.sent)[0].token_symbol}
        </div>
      `;
      }

      // conditionally append HTML for received amount if it exists
      if (transaction_info.received) {
        html += `
        <div>
          <span class="transaction-received-amount">+${
            Object.values(transaction_info.received)[0].final_amount
          }</span>
          ${Object.values(transaction_info.received)[0].token_symbol}
        </div>
      `;
      }

      // close the transaction container div
      html += `</div>`;
      return html;
    }
    let transactionsContainer = document.getElementById(
      "wallet-transactions-container"
    );

    Object.entries(data).forEach(([hash, tdata]) => {
      let newHtml = createTransactionsEntry(hash, tdata);
      transactionsContainer.innerHTML += newHtml;
    });
  }

  function handleTransactionDetailsMessage(data) {
    console.log("handleTransactionDetailssMessage");
  }

  function handleCurrentTokenPricesMessage(data) {
    // parse the current token prices object sent via channels and add the current prices to the already created balances entries
    console.log("handleCurrentTokenPricesMessage");
    if (walletDataStatus === "ready") {
      // ignore the new prices
      return;
    }

    Object.keys(data).forEach((contract) => {
      let balanceDiv = document.querySelector(
        `#balance-${contract} > .balance-usd-value`
      );
      let lastCheckedDiv = document.querySelector(
        `#balance-${contract} > .balance-token-last-checked-price-usd`
      );
      let iconElement = document.querySelector(
        `#balance-${contract} .balance-token-icon`
      );

      // add usd value
      if (balanceDiv) {
        balanceDiv.innerHTML = `$${parseFloat(
          data[contract]?.usd_value
        ).toFixed(2)}`;

        if (data[contract]?.usd_value < 2) {
          let balanceElementContainer = document.querySelector(
            `#balance-${contract}`
          );
          balanceElementContainer.classList.add("small-balance");
        }
      }

      // add last checked token price value
      if (lastCheckedDiv) {
        lastCheckedDiv.innerHTML = `$${data[contract]?.price_usd}`;
      }

      // add token image
      if (iconElement && data[contract].token_image_url) {
        iconElement.src = data[contract].token_image_url;
      }
    });

    // sort the items in the current order
    sortBalancesList();
  }

  function handleSuspiciousDataMessage(data) {
    const suspBalances = data["suspicious_balances"];
    const suspTransactions = data["suspicious_transactions"];
    suspBalances.forEach((contract) => {
      const balanceElement = document.querySelector(`#balance-${contract}`);
      balanceElement.remove();
    });
    markToBeHidden();
    suspTransactions.forEach((hash) => {
      const transactionElement = document.querySelector(`#transaction-${hash}`);
      transactionElement.remove();
    });
  }

  function handleFinalizedUsdPricesMessage(data) {
    console.log("handleFinalizedUsdPricesMessage");
  }

  function handleHistoricBalancesPLMessage(data) {
    console.log("handleHistoricBalancesPLMessage");
  }

  function handleTokensAndWalletPLMessage(data) {
    console.log("handleTokensAndWalletPLMessage");
    const elementQueries = {
      total: "total-wallet-p-l",
      total_wallet_sold: "amount_received_from_selling",
      total_wallet_spent: "amount_spent_for_purchases",
      wallet_realized_p_l: "realized-wallet-p-l",
      total_usd_value: "current-wallet-usd-balance",
    };
    Object.keys(data).forEach((contract) => {
      if (contract in elementQueries) {
        const elementToUpdate = document.querySelector(
          `.${elementQueries[contract]} > .value`
        );
        elementToUpdate.innerHTML = `${parseFloat(data[contract].toFixed(2))}`;
      } else {
        let tokenPLDiv = document.querySelector(
          `#balance-${contract} > .balance-token-p-l`
        );
        if (tokenPLDiv && data[contract]) {
          tokenPLDiv.innerHTML = `$${parseFloat(data[contract]).toFixed(2)}`;
        }
      }
    });
  }

  function handleUpdateAvailableMessage(data) {
    console.log(data);
    const updateNotification = document.querySelector(".update-notification > .notification-icon");
    if (data === true) {
      updateNotification.classList.remove("hidden");

      updateNotification.addEventListener("click", () => {
        location.reload();
      });
    }
  }
};

function attachSortingEventListeners() {
  document
    .querySelector(`.balance-header > .balance-usd-value`)
    .addEventListener(
      "mousedown",
      () => {
        toggleSortState("balances", "balance-usd-value");
      },
      true
    );

  document
    .querySelector(`.balance-header > .balance-token-p-l`)
    .addEventListener(
      "mousedown",
      () => {
        const newState = toggleSortState("balances", "balance-token-p-l");
      },
      true
    );
}

function markSmallBalances() {
  const balanceContainer = document.getElementById("balance-outer-container");
  const items = Array.from(balanceContainer.children);

  items.forEach((item) => {
    balanceValue = parseFloat(
      item.querySelector(".balance-usd-value").textContent.replace("$", "")
    );
    if (balanceValue < 2) {
      item.classList.add("small-balance");
    }
  });
}

/**
 * Toggles the selected sort state and calls the sort function
 *
 * @param   section  The section of the website to toggle sort for.
 * @param   field The field by which to sort.
 */
function toggleSortState(section, field) {
  if (section in sortStates) {
    currentOrder = sortStates[section];
    if (currentOrder["field"] === field) {
      currentOrder["order"] = currentOrder["order"] === "asc" ? "desc" : "asc";
    } else {
      currentOrder["field"] = field;
      currentOrder["order"] = "desc";
    }
    sortBalancesList();
  }
}

function markToBeHidden() {
  const balanceContainer = document.getElementById("balance-outer-container");
  const items = Array.from(balanceContainer.children);
  let count = 0;
  items.forEach((item) => {
    if (count >= 10) {
      item.classList.add("to-be-hidden");
      if (!showAllBalanceItems) {
        item.classList.add("hidden");
      }
    } else {
      item.classList.remove("to-be-hidden");
      if (!item.classList.contains("small-balance") || !hideSmallBalances) {
        item.classList.remove("hidden");
        count += 1;
      }
    }
  });
}
function sortBalancesList() {
  const balanceContainer = document.getElementById("balance-outer-container");
  const items = Array.from(balanceContainer.children);
  sort_by = sortStates?.balances?.field;
  ord = sortStates?.balances?.order;

  items.sort((a, b) => {
    const aValue =
      parseFloat(a.querySelector(`.${sort_by}`).textContent.replace("$", "")) ||
      0;
    const bValue =
      parseFloat(b.querySelector(`.${sort_by}`).textContent.replace("$", "")) ||
      0;

    if (ord === "desc") {
      return bValue - aValue;
    } else {
      return aValue - bValue;
    }
  });

  // Clear the container and re-append sorted items
  balanceContainer.innerHTML = "";
  let count = 0;
  items.forEach((item) => {
    if (count >= 10) {
      item.classList.add("to-be-hidden");
      if (!showAllBalanceItems) {
        item.classList.add("hidden");
      }
    } else {
      item.classList.remove("to-be-hidden");
      if (!item.classList.contains("small-balance") || !hideSmallBalances) {
        item.classList.remove("hidden");
        count += 1;
      }
    }
    balanceContainer.appendChild(item);
  });
}

function handleShowAllItems() {
  showAllBalanceItems = showAllBalanceItems === true ? false : true;

  let items = document.querySelectorAll("#balances .to-be-hidden");
  items.forEach(function (item) {
    if (!hideSmallBalances || !item.classList.contains("small-balance")) {
      item.classList.toggle("hidden");
    }
  });
}

function handleHideSmallBalances() {
  hideSmallBalances = hideSmallBalances === true ? false : true;
  const smallBalances = document.querySelectorAll("#balances .small-balance");
  smallBalances.forEach((item) => {
    if (hideSmallBalances) {
      item.classList.add("hidden");
    } else {
      if (!item.classList.contains("to-be-hidden") || showAllBalanceItems) {
        item.classList.remove("hidden");
      }
    }
  });
  markToBeHidden();
}
