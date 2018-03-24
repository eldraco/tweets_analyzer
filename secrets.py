# Go to http://dev.twitter.com and create an app.
# The consumer key and secret will be generated for you after
consumer_key="xxxxxxxxxxxxxx"
consumer_secret="xxxxxxxxxxxxx"

# After the step above, you will be redirected to your app's page.
# Create an access token under the the "Your access token" section
access_token="xxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxxxxx"
access_token_secret="xxxxxxxxxxxxxxxxxxxxxxx"

# API for repustate sentiment analysis. Get you API key for free from https://www.repustate.com
from repustate import Client
repustate_client = Client(api_key='xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx', version='v3')

