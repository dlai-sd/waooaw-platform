# employment_air_client.EmploymentInterpretationApi

All URIs are relative to *https://ai-runtime.internal.waooaw*

Method | HTTP request | Description
------------- | ------------- | -------------
[**get_employment_patch_proposal**](EmploymentInterpretationApi.md#get_employment_patch_proposal) | **GET** /internal/v1/employment-patch-proposals/{proposalId} | Reconcile one immutable proposal result
[**propose_employment_patch**](EmploymentInterpretationApi.md#propose_employment_patch) | **POST** /internal/v1/employment-patch-proposals | Produce or replay one non-authoritative typed employment patch proposal


# **get_employment_patch_proposal**
> EmploymentPatchProposalV1 get_employment_patch_proposal(proposal_id, x_correlation_id)

Reconcile one immutable proposal result

Returns the immutable proposal result or an explicit unavailable outcome without fabricating a patch.

### Example

* Bearer (JWT) Authentication (ServiceBearerAuth):

```python
import employment_air_client
from employment_air_client.models.employment_patch_proposal_v1 import EmploymentPatchProposalV1
from employment_air_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://ai-runtime.internal.waooaw
# See configuration.py for a list of all supported configuration parameters.
configuration = employment_air_client.Configuration(
    host = "https://ai-runtime.internal.waooaw"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure Bearer authorization (JWT): ServiceBearerAuth
configuration = employment_air_client.Configuration(
    access_token = os.environ["BEARER_TOKEN"]
)

# Enter a context with an instance of the API client
with employment_air_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = employment_air_client.EmploymentInterpretationApi(api_client)
    proposal_id = 'proposal_id_example' # str | 
    x_correlation_id = 'x_correlation_id_example' # str | 

    try:
        # Reconcile one immutable proposal result
        api_response = api_instance.get_employment_patch_proposal(proposal_id, x_correlation_id)
        print("The response of EmploymentInterpretationApi->get_employment_patch_proposal:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling EmploymentInterpretationApi->get_employment_patch_proposal: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **proposal_id** | **str**|  | 
 **x_correlation_id** | **str**|  | 

### Return type

[**EmploymentPatchProposalV1**](EmploymentPatchProposalV1.md)

### Authorization

[ServiceBearerAuth](../README.md#ServiceBearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json, application/problem+json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Proposal result |  -  |
**401** | Invalid service assertion |  -  |
**404** | Proposal absent or inaccessible |  -  |
**503** | Inference unavailable; no proposal is fabricated |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **propose_employment_patch**
> EmploymentPatchProposalV1 propose_employment_patch(idempotency_key, x_correlation_id, employment_patch_proposal_request_v1)

Produce or replay one non-authoritative typed employment patch proposal

Interprets one bounded contribution into a proposal that BP must independently validate and confirm.

### Example

* Bearer (JWT) Authentication (ServiceBearerAuth):

```python
import employment_air_client
from employment_air_client.models.employment_patch_proposal_request_v1 import EmploymentPatchProposalRequestV1
from employment_air_client.models.employment_patch_proposal_v1 import EmploymentPatchProposalV1
from employment_air_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://ai-runtime.internal.waooaw
# See configuration.py for a list of all supported configuration parameters.
configuration = employment_air_client.Configuration(
    host = "https://ai-runtime.internal.waooaw"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure Bearer authorization (JWT): ServiceBearerAuth
configuration = employment_air_client.Configuration(
    access_token = os.environ["BEARER_TOKEN"]
)

# Enter a context with an instance of the API client
with employment_air_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = employment_air_client.EmploymentInterpretationApi(api_client)
    idempotency_key = 'idempotency_key_example' # str | 
    x_correlation_id = 'x_correlation_id_example' # str | 
    employment_patch_proposal_request_v1 = employment_air_client.EmploymentPatchProposalRequestV1() # EmploymentPatchProposalRequestV1 | 

    try:
        # Produce or replay one non-authoritative typed employment patch proposal
        api_response = api_instance.propose_employment_patch(idempotency_key, x_correlation_id, employment_patch_proposal_request_v1)
        print("The response of EmploymentInterpretationApi->propose_employment_patch:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling EmploymentInterpretationApi->propose_employment_patch: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **idempotency_key** | **str**|  | 
 **x_correlation_id** | **str**|  | 
 **employment_patch_proposal_request_v1** | [**EmploymentPatchProposalRequestV1**](EmploymentPatchProposalRequestV1.md)|  | 

### Return type

[**EmploymentPatchProposalV1**](EmploymentPatchProposalV1.md)

### Authorization

[ServiceBearerAuth](../README.md#ServiceBearerAuth)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json, application/problem+json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**202** | Proposal responsibility accepted |  -  |
**200** | Identical immutable proposal replayed |  -  |
**400** | Invalid closed request |  -  |
**401** | Invalid service assertion |  -  |
**409** | Idempotency or exact-version conflict |  -  |
**422** | Contribution cannot be represented in the allowed semantic path catalogue |  -  |
**503** | Inference unavailable; no proposal is fabricated |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

