
import requests
import sys
import json

class WalletNFTHistory: 
    wallet = None
    nfts = {}

    def __init__(self, wallet):
        self.wallet = wallet
    
    def processOpenseaAPIResponse(self, openseaEvents):
        
        #debug only
        #print(json.dumps(openseaEvents,indent=4))
        
        # Process all events from the API
        # Each transaction will either create a new NFT object or add a buy/sell transaction to an existing NFT
        for openseaEvent in openseaEvents['asset_events']:
            event_type = openseaEvent['event_type']

            #id of asset
            asset_id = openseaEvent['asset']['asset_contract']['address'] + '-' + openseaEvent['asset']['token_id']
            
            # payment_token maybe null, so cannot chain easily in python
            payment_token = openseaEvent.get('payment_token')
            if payment_token is not None:
                ethereum_usd_price_now = float(payment_token.get('usd_price'))
                price_in_wei = float(openseaEvent['total_price'])
                payment_token = payment_token.get('symbol')
                usd_price = (price_in_wei*1.0e-18)*ethereum_usd_price_now
            else:
                usd_price=None

            if event_type=='successful':
                transaction  = Transaction(openseaEvent['transaction']['transaction_hash'],price_in_wei,openseaEvent['quantity'], payment_token, usd_price, openseaEvent['seller']['address'], openseaEvent['winner_account']['address'])
            elif event_type=='transfer':
                transaction  = Transaction(openseaEvent['transaction']['transaction_hash'],price_in_wei,openseaEvent['quantity'], payment_token, usd_price, openseaEvent['from_account']['address'], openseaEvent['to_account']['address'])
            #print(transaction)

            # Create new NFT or add transaction to existing NFT
            if asset_id not in self.nfts:
                #print('New NFT found')
                nft  = NFT(openseaEvent['asset']['asset_contract']['address'] ,openseaEvent['asset']['name'],openseaEvent['asset']['description'],openseaEvent['asset']['token_id'],openseaEvent['asset']['permalink'],openseaEvent['asset']['image_url'],openseaEvent['asset']['image_preview_url'],)   
            else:
                #print('Add transaction to existing NFT')
                nft = self.nfts.get(asset_id)
                
            if transaction.isSeller(self.wallet):
                nft.sellTransaction = transaction
            else:
                nft.buyTransaction = transaction
            
            self.nfts[asset_id]= nft
        

    def listNFTs(self):
        
        #NFTs with both buy and sold transaction
        print("NFT profits:")
        print('"NFT name"\tProfit:\tSell price:\tBuy price:')
        profits = 0.0
        for nftKey in self.nfts:
            nft = self.nfts[nftKey]
            if nft.buyTransaction and nft.sellTransaction:
                print(nft)
                profits += nft.getProfits()

        print("Profits (USD) {:.2f}".format(profits))

class NFT:
    buyTransaction = None
    sellTransaction = None

    def __init__(self, contractAddress,nftName,nftDescription,contractTokenId,openseaLink,imageUrl,imagePreviewUrl):
        self.contractAddress = contractAddress
        self.nftName = nftName
        self.nftDescription = nftDescription
        self.contractTokenId = contractTokenId
        self.openseaLink = openseaLink
        self.imageUrl = imageUrl
        self.imagePreviewUrl = imagePreviewUrl

    def __str__(self):
        if self.buyTransaction and self.sellTransaction:
            return '{}\t{:.2f}\t{:.2f}\t{:.2f}'.format(self.nftName , self.sellTransaction.usdPrice- self.buyTransaction.usdPrice, self.sellTransaction.usdPrice,self.buyTransaction.usdPrice)
        elif self.buyTransaction:
            return '{}\t\t\t{:.2f}'.format(self.nftName,self.buyTransaction.usdPrice)
        elif self.sellTransaction:
            return '{}\t\t{:.2f}\t'.format(self.nftName,self.sellTransaction.usdPrice)     
        #return  str(self.__class__) + ' - '+ ','.join(('{} = {}'.format(item, self.__dict__[item]) for item in self.__dict__))

    def getProfits(self):
        if self.buyTransaction and self.sellTransaction:
            return self.sellTransaction.usdPrice- self.buyTransaction.usdPrice
        else:
            return 0.0

class Transaction:
    def __init__(self, transactionHash,price,quantity,paymentToken, usdPrice, walletSeller, walletBuyer):
        self.transactionHash=transactionHash
        self.price = price
        self.quantity = quantity
        self.paymentToken=paymentToken
        self.usdPrice=usdPrice
        self.walletSeller=walletSeller
        self.walletBuyer= walletBuyer

    def isSeller(self,wallet):
        if self.walletSeller==wallet:
            return True
        else: 
            return False

    def isBuyer(self,wallet):
        if self.walletBuyer==wallet:
            return True
        else: 
            return False

    

    def __str__(self):
        return  'Transaction: '+ ','.join(('{} = {}'.format(item, self.__dict__[item]) for item in self.__dict__))                        


def main():
    wallet = sys.argv[1]
    #openseaAPIKey = sys.argv[1]
    walletNFTHistory = WalletNFTHistory(wallet)


    query = {   'account_address':wallet, 
                'event_type':'successful', 
                #'event_type':'transfer',
                'only_opensea':False,
                #'occured_before':'31.12.2021',  #Needs to be unix epoch style
                #'occured_after':'01.01.2021',
                'offset': 0,
                'limit':200}

    headers = { #'X-API-KEY': openseaAPIKey,
                'Accepts':'application/json'}      
    #print(query)
    try:
        response = requests.get('https://api.opensea.io/api/v1/events', params=query,headers=headers)
        response.raise_for_status()

        openseaEvents = response.json()
        walletNFTHistory.processOpenseaAPIResponse(openseaEvents)
        walletNFTHistory.listNFTs()
        # Additional code will only run if the request is successful
    except requests.exceptions.HTTPError as error:
        print(error)
    #


if __name__ == '__main__':
   main()