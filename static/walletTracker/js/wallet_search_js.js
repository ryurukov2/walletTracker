var start = function () {
  // global variables from wallet_search template
  console.log(queriedAddress)

  // Establishes channels connection
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
    // Parses the balances object sent via channels and generates the HTML to display them
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
    // Parses the transactions object sent via channels and generates HTML to display them
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
    // Parses the current token prices object sent via channels and adds the current prices to the already created balances entries
    console.log("handleCurrentTokenPricesMessage");

    const balancesDiv = document.querySelector("#balances > div > ul");
    Object.keys(data).forEach((contract) => {
      let balanceDiv = document.querySelector(
        `#balance-${contract} > .balance-usd-value`
      );
      let lastCheckedDiv = document.querySelector(
        `#balance-${contract} > .balance-token-last-checked-price-usd`
      );
      let iconElement = document.querySelector(`#balance-${contract} .balance-token-icon`);
      if (balanceDiv) {
        balanceDiv.innerHTML = `$${parseFloat(data[contract]?.usd_value).toFixed(2)}`;
      }
      if (lastCheckedDiv) {
        lastCheckedDiv.innerHTML = `$${data[contract]?.latest_price}`;
      }
      if (iconElement && data[contract].token_image_url){
        iconElement.src = data[contract].token_image_url;
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
    const elementQueries = {
      'total': 'total-wallet-p-l',
      'total_wallet_sold': 'amount_received_from_selling',
      'total_wallet_spent': 'amount_spent_for_purchases',
      'wallet_realized_p_l': 'realized-wallet-p-l',
      'total_usd_value': 'current-wallet-usd-balance'
    }
    Object.keys(data).forEach((contract) => {
      if(contract in elementQueries){
        const elementToUpdate = document.querySelector(`.${elementQueries[contract]} > .value`)
        elementToUpdate.innerHTML = `${parseFloat(data[contract].toFixed(2))}`
      }else{
      let tokenPLDiv = document.querySelector(
        `#balance-${contract} > .balance-token-p-l`
      );
      if (tokenPLDiv && data[contract]) {
        tokenPLDiv.innerHTML = `$${parseFloat(data[contract]).toFixed(2)}`;
      }
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

};

function showAllItems() {
  var items = document.querySelectorAll("#balances .to-be-hidden");
  items.forEach(function (item) {
    item.classList.toggle("hidden");
  });
}
