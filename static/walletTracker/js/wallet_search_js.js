var start = function () {
  var es = new ReconnectingEventSource("/events/");
  es.onopen = function () {
    console.log("connected");
    const currentTime = Date.now();
    console.log(currentTime);
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

  function handleBalancesMessage(data) {
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
    console.log("handleTransactionsMessage");

    function createTransactionsEntry(hash, transaction_info) {
      let html = "";
      ts = new Date(transaction_info.timeStamp * 1000).toLocaleString();
      sent_data = transaction_info.sent;
      html += `<div id="transaction-${hash}" class="transaction-container">`;

      // Placeholder for the timestamp
      html += `<span class="transaction-timestamp">${ts}</span>`;

      // Conditionally append HTML for sent amount if it exists
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

      // Conditionally append HTML for received amount if it exists
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

      // Close the transaction container div
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
    console.log("handleCurrentTokenPricesMessage");

    const balancesDiv = document.querySelector("#balances > div > ul");
    Object.keys(data).forEach((contract) => {
      let balanceDiv = document.querySelector(
        `#balance-${contract} > .balance-usd-value`
      );
      let lastCheckedDiv = document.querySelector(
        `#balance-${contract} > .balance-token-last-checked-price-usd`
      );
      if (balanceDiv) {
        balanceDiv.innerHTML = `${data[contract].usd_value}`;
      }
      if (lastCheckedDiv) {
        lastCheckedDiv.innerHTML = `${data[contract].latest_price}`;
      }
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
    Object.keys(data).forEach((contract) => {
      if (contract == "total") {
      } else if (contract == "total_wallet_sold") {
      } else if (contract == "total_") {
      }
      let tokenPLDiv = document.querySelector(
        `#balance-${contract} > .balance-token-p-l`
      );
      if (tokenPLDiv && data[contract]) {
        tokenPLDiv.innerHTML = `${data[contract]}`;
      }
    });
  }

  const messageHandlers = {
    balances: handleBalancesMessage,
    transactions: handleTransactionsMessage,
    transactions_details: handleTransactionDetailsMessage,
    current_token_prices: handleCurrentTokenPricesMessage,
    finalized_usd_prices: handleFinalizedUsdPricesMessage,
    historic_balances_p_l: handleHistoricBalancesPLMessage,
    tokens_and_wallet_p_l_info: handleTokensAndWalletPLMessage,
  };
  es.addEventListener(
    "message",
    function (e) {
      let resp = JSON.parse(e.data);
      console.log(resp);
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

  function updateBalancesHTML(data) {
    const balancesDiv = document.querySelector("#balances > div > ul");

    // Check if the item already exists to prevent duplicates
    let existingItem = document.getElementById(`balance-${data.tokenSymbol}`);
    if (!existingItem) {
      // Create new list item
      let listItem = document.createElement("li");
      listItem.id = `balance-${data.tokenSymbol}`; // Assign an ID for potential updates
      listItem.innerHTML = `${data.tokenSymbol}: ${data.balance} | ${data.usd_value}`;
      console.log("no existing item, create");
      balancesDiv.appendChild(listItem);
    } else {
      // Update existing item
      existingItem.innerHTML = `${data.tokenSymbol}: ${data.balance} | ${data.usd_value}`;
    }
  }

  function updateTransactionsHTML(data) {
    const balancesDiv = document.querySelector("#balances > div > ul");

    // Check if the item already exists to prevent duplicates
    let existingItem = document.getElementById(`balance-${data.tokenSymbol}`);
    if (!existingItem) {
      // Create new list item
      let listItem = document.createElement("li");
      listItem.id = `balance-${data.tokenSymbol}`; // Assign an ID for potential updates
      listItem.innerHTML = `${data.tokenSymbol}: ${data.balance} | ${data.usd_value}`;
      console.log("no existing item, create");
      balancesDiv.appendChild(listItem);
    } else {
      // Update existing item
      existingItem.innerHTML = `${data.tokenSymbol}: ${data.balance} | ${data.usd_value}`;
    }
  }
};

function showAllItems() {
  var items = document.querySelectorAll("#balances .to-be-hidden");
  items.forEach(function (item) {
    item.classList.toggle("hidden");
  });
}
