import pandas as pd
from pandas.io.json import json_normalize #this is a crutial, and awesome library. if you work with json, you need this in your life
import numpy as np 
import matplotlib.pyplot as plt
import json, re, os, yagmail
from datetime import datetime, timedelta
from pprint import pprint

# These two modules are a collection of custom functions built to connect
# and gather information from unleashed software via it's api.
from ulConnect import getULData, convertDateToDate
from WatchDog import getAllSOH, getSOH

r = getULData('SalesOrders/', 'pageSize=1000&orderStatus=Parked')
sales_orders_df = pd.read_json(json.dumps(r.json()['Items']))

sales_order_lines_df = json_normalize(r.json()['Items'],record_path='SalesOrderLines', meta=['OrderNumber', 'RequiredDate', 'CreatedOn'])
parked_products = json_normalize(sales_order_lines_df.Product)
sales_order_lines_df['ProductCode'] = parked_products.ProductCode
sales_order_lines_df.CreatedOn = sales_order_lines_df.CreatedOn.apply(convertDateToDate)
sales_order_lines_df.RequiredDate = sales_order_lines_df.RequiredDate.apply(convertDateToDate)
try:
	stock_on_hand_df = pd.read_json('stockOnHand_IW.json')
except:
	getSOH()
	stock_on_hand_df = pd.read_json('stockOnHand_IW.json')

so_to_order = []
# iterate over the sales_order_lines_df for products
for idx, row in sales_order_lines_df.iterrows():
#     Determine jsut the soh pertaining to a single product code
    temp = stock_on_hand_df[stock_on_hand_df['ProductCode'] == row['ProductCode']]
#     We need to exclude the delivery code, and make sure there is a value returned by the SOH df
    if row['ProductCode'] != 'Delivery' and len(temp) > 0:

#          Make a little detour to get the supplier information on this product
        r = getULData('Products', 'productCode='+row['ProductCode'])
        p = json_normalize(r.json()['Items'])
#         Here we actually grab the supplier's name.
        sup_name = p['Supplier.SupplierName'].values[0]
#         use that supplier name to determine the average and std time to complete a po from that supplier
        mean_time_to_complete = po_df[po_df['SupplierName'] == sup_name]['Time_To_Complete'].mean()
        std_time_to_complete = po_df[po_df['SupplierName'] == sup_name]['Time_To_Complete'].std()
        
        #determine if that time is greater or equal to the time from now until when the customer needs the product
        # and if so, append the order to the list of orders to order :-P
        need_by_delta = row['RequiredDate'] - datetime.today()
        po_receive_delta = mean_time_to_complete + std_time_to_complete

#         AvailableQty can be negative or positive, onPurchase is only ever >=0
        val = (temp['AvailableQty'].values[0] + temp['OnPurchase'].values[0])
        if val < 0 and (need_by_delta <= po_receive_delta):
#             Finally, append all the data the inside sales team is going to need in order to order the correct product and quantities.
            so_to_order.append([row['OrderNumber'], row['ProductCode'], row['OrderQuantity'], row['RequiredDate']])


so_to_order = pd.DataFrame(so_to_order, columns=['Order Number', 'Product', 'Amount Needed','Required Date'])
html = '<!DOCTYPE html><html><body><h1>Sales orders that should be submitted as POs today:</h1><p></p></body></html>'
jon = 'jon@iwhardwood.com'
yag = yagmail.SMTP(user='jon@iwhardwood.com', password='Pass4iwgmail')
yag.send(to=jon,subject='Test', contents=[html] )