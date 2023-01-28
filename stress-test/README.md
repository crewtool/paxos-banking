Stress tests were performed on europe-west2 server, due to unavailability of europe-central2.

To run tests you first need to run cluster and open the account.
Then download Apache JMeter, open stress-test.jmx, fill IP adress and account_id in HTTP Request 'Add money' and run the tests.
If you want results saved as csv file add Filename to Aggregate Report.
The default settings are: 1 user, 60 second of test, 0 delay between requests.
