import threading

from django.views.generic import ListView
from django.conf import settings
from django.shortcuts import render, redirect
from dotenv import load_dotenv
from .models import Transaction
from .utils.logic import wallet_calaulations_thread_worker
from .utils.database_connections import wallet_data_available_in_db
load_dotenv()



def index(request):
    'Homepage view'
    return render(request, 'index.html')

def wallet_search(request):
    'Wallet search view'
    if request.method == 'POST':
        # print(request.__dict__)
        address_queried = request.POST.get('address')
        # check if data available in DB ( and if recent)
        # if yes - redirect to GET/{wallet}
        # if no - full API+data processing flow, then redirect to GET/{wallet}

        # return render(request, 'wallet/wallet_results.html')
        return redirect(f'/wallet/search/?address={address_queried}')
    elif request.method == 'GET':
        # check if data available in DB (and if recent)
        # if yes = render it
        # if not = redirect to the search page
        address_queried = request.GET.get('address')
        if not address_queried:
            return render(request, 'wallet/wallet_search.html')

        data_from_db = wallet_data_available_in_db(address_queried)
        if not data_from_db:
            wallet_data = {"data_status": 'pending'}
            thread = threading.Thread(
                target=wallet_calaulations_thread_worker, args=(address_queried,))
            thread.daemon = True
            thread.start()
        else:
            wallet_data = {"data_status": "ready", "wallet_info": data_from_db}
        return render(request, 'wallet/wallet_search.html', context={'address': address_queried, 'wallet_data': wallet_data})



class TransactionsListView(ListView):
    model = Transaction
    paginate_by = 20

    def get_queryset(self):
        wallet_address = self.kwargs['wallet_address']
        return Transaction.objects.filter(related_wallet=wallet_address)