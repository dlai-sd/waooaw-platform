# employment_domain_client.EmploymentDomainSemanticsApi

All URIs are relative to *https://domain-adapter.internal.waooaw*

Method | HTTP request | Description
------------- | ------------- | -------------
[**classify_material_change**](EmploymentDomainSemanticsApi.md#classify_material_change) | **POST** /internal/v1/relationships/{relationshipId}/employment/material-change-classification | Classify domain materiality and affected work without changing plan state
[**evaluate_dependency_isolation**](EmploymentDomainSemanticsApi.md#evaluate_dependency_isolation) | **POST** /internal/v1/relationships/{relationshipId}/employment/dependency-isolation | Prove or reject bounded Skill isolation after dependency change
[**get_employment_interface_manifest**](EmploymentDomainSemanticsApi.md#get_employment_interface_manifest) | **GET** /internal/v1/employment-interface/manifest | Resolve one exact immutable agent employment interface manifest
[**get_induction_requirement_set**](EmploymentDomainSemanticsApi.md#get_induction_requirement_set) | **GET** /internal/v1/relationships/{relationshipId}/employment/induction-requirements | Get profession-specific induction requirements in generic envelopes
[**get_performance_assessment**](EmploymentDomainSemanticsApi.md#get_performance_assessment) | **GET** /internal/v1/relationships/{relationshipId}/employment/performance-assessments/{reviewPeriodRef} | Get domain business-outcome and agent-performance meanings separately
[**validate_plan_candidate**](EmploymentDomainSemanticsApi.md#validate_plan_candidate) | **POST** /internal/v1/relationships/{relationshipId}/employment/plan-validation | Validate domain semantics without accepting or authorizing the plan


# **classify_material_change**
> MaterialChangeAssessmentV1 classify_material_change(relationship_id, idempotency_key, x_correlation_id, material_change_request_v1)

Classify domain materiality and affected work without changing plan state

Returns domain materiality and affected references; protected BP materiality categories remain mandatory.

### Example

* Bearer (JWT) Authentication (ServiceBearerAuth):

```python
import employment_domain_client
from employment_domain_client.models.material_change_assessment_v1 import MaterialChangeAssessmentV1
from employment_domain_client.models.material_change_request_v1 import MaterialChangeRequestV1
from employment_domain_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://domain-adapter.internal.waooaw
# See configuration.py for a list of all supported configuration parameters.
configuration = employment_domain_client.Configuration(
    host = "https://domain-adapter.internal.waooaw"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure Bearer authorization (JWT): ServiceBearerAuth
configuration = employment_domain_client.Configuration(
    access_token = os.environ["BEARER_TOKEN"]
)

# Enter a context with an instance of the API client
with employment_domain_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = employment_domain_client.EmploymentDomainSemanticsApi(api_client)
    relationship_id = 'relationship_id_example' # str | 
    idempotency_key = 'idempotency_key_example' # str | 
    x_correlation_id = 'x_correlation_id_example' # str | 
    material_change_request_v1 = employment_domain_client.MaterialChangeRequestV1() # MaterialChangeRequestV1 | 

    try:
        # Classify domain materiality and affected work without changing plan state
        api_response = api_instance.classify_material_change(relationship_id, idempotency_key, x_correlation_id, material_change_request_v1)
        print("The response of EmploymentDomainSemanticsApi->classify_material_change:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling EmploymentDomainSemanticsApi->classify_material_change: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **relationship_id** | **str**|  | 
 **idempotency_key** | **str**|  | 
 **x_correlation_id** | **str**|  | 
 **material_change_request_v1** | [**MaterialChangeRequestV1**](MaterialChangeRequestV1.md)|  | 

### Return type

[**MaterialChangeAssessmentV1**](MaterialChangeAssessmentV1.md)

### Authorization

[ServiceBearerAuth](../README.md#ServiceBearerAuth)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json, application/problem+json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Domain materiality assessment |  -  |
**400** | Invalid generic envelope or unsupported domain reference |  -  |
**401** | Invalid service assertion, audience, purpose or relationship delegation |  -  |
**409** | Idempotency, exact-version or source conflict |  -  |
**503** | Adapter cannot provide current domain meaning |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **evaluate_dependency_isolation**
> DependencyIsolationAssessmentV1 evaluate_dependency_isolation(relationship_id, idempotency_key, x_correlation_id, dependency_isolation_request_v1)

Prove or reject bounded Skill isolation after dependency change

Proves bounded isolation or returns unknown so BP can fail closed for dependent work.

### Example

* Bearer (JWT) Authentication (ServiceBearerAuth):

```python
import employment_domain_client
from employment_domain_client.models.dependency_isolation_assessment_v1 import DependencyIsolationAssessmentV1
from employment_domain_client.models.dependency_isolation_request_v1 import DependencyIsolationRequestV1
from employment_domain_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://domain-adapter.internal.waooaw
# See configuration.py for a list of all supported configuration parameters.
configuration = employment_domain_client.Configuration(
    host = "https://domain-adapter.internal.waooaw"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure Bearer authorization (JWT): ServiceBearerAuth
configuration = employment_domain_client.Configuration(
    access_token = os.environ["BEARER_TOKEN"]
)

# Enter a context with an instance of the API client
with employment_domain_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = employment_domain_client.EmploymentDomainSemanticsApi(api_client)
    relationship_id = 'relationship_id_example' # str | 
    idempotency_key = 'idempotency_key_example' # str | 
    x_correlation_id = 'x_correlation_id_example' # str | 
    dependency_isolation_request_v1 = employment_domain_client.DependencyIsolationRequestV1() # DependencyIsolationRequestV1 | 

    try:
        # Prove or reject bounded Skill isolation after dependency change
        api_response = api_instance.evaluate_dependency_isolation(relationship_id, idempotency_key, x_correlation_id, dependency_isolation_request_v1)
        print("The response of EmploymentDomainSemanticsApi->evaluate_dependency_isolation:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling EmploymentDomainSemanticsApi->evaluate_dependency_isolation: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **relationship_id** | **str**|  | 
 **idempotency_key** | **str**|  | 
 **x_correlation_id** | **str**|  | 
 **dependency_isolation_request_v1** | [**DependencyIsolationRequestV1**](DependencyIsolationRequestV1.md)|  | 

### Return type

[**DependencyIsolationAssessmentV1**](DependencyIsolationAssessmentV1.md)

### Authorization

[ServiceBearerAuth](../README.md#ServiceBearerAuth)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json, application/problem+json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Isolation assessment |  -  |
**400** | Invalid generic envelope or unsupported domain reference |  -  |
**401** | Invalid service assertion, audience, purpose or relationship delegation |  -  |
**409** | Idempotency, exact-version or source conflict |  -  |
**503** | Adapter cannot provide current domain meaning |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_employment_interface_manifest**
> EmploymentInterfaceManifestV1 get_employment_interface_manifest(agent_type, agent_version, manifest_version, x_correlation_id)

Resolve one exact immutable agent employment interface manifest

Returns exact protocol and manifest support without reading mutable repository text at action time.

### Example

* Bearer (JWT) Authentication (ServiceBearerAuth):

```python
import employment_domain_client
from employment_domain_client.models.employment_interface_manifest_v1 import EmploymentInterfaceManifestV1
from employment_domain_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://domain-adapter.internal.waooaw
# See configuration.py for a list of all supported configuration parameters.
configuration = employment_domain_client.Configuration(
    host = "https://domain-adapter.internal.waooaw"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure Bearer authorization (JWT): ServiceBearerAuth
configuration = employment_domain_client.Configuration(
    access_token = os.environ["BEARER_TOKEN"]
)

# Enter a context with an instance of the API client
with employment_domain_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = employment_domain_client.EmploymentDomainSemanticsApi(api_client)
    agent_type = 'agent_type_example' # str | 
    agent_version = 'agent_version_example' # str | 
    manifest_version = 'manifest_version_example' # str | 
    x_correlation_id = 'x_correlation_id_example' # str | 

    try:
        # Resolve one exact immutable agent employment interface manifest
        api_response = api_instance.get_employment_interface_manifest(agent_type, agent_version, manifest_version, x_correlation_id)
        print("The response of EmploymentDomainSemanticsApi->get_employment_interface_manifest:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling EmploymentDomainSemanticsApi->get_employment_interface_manifest: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **agent_type** | **str**|  | 
 **agent_version** | **str**|  | 
 **manifest_version** | **str**|  | 
 **x_correlation_id** | **str**|  | 

### Return type

[**EmploymentInterfaceManifestV1**](EmploymentInterfaceManifestV1.md)

### Authorization

[ServiceBearerAuth](../README.md#ServiceBearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json, application/problem+json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Exact manifest |  -  |
**401** | Invalid service assertion, audience, purpose or relationship delegation |  -  |
**404** | Resource absent or inaccessible |  -  |
**503** | Adapter cannot provide current domain meaning |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_induction_requirement_set**
> InductionRequirementSetV1 get_induction_requirement_set(relationship_id, manifest_version, x_correlation_id)

Get profession-specific induction requirements in generic envelopes

Returns versioned domain requirements and affected Skills without owning BP readiness.

### Example

* Bearer (JWT) Authentication (ServiceBearerAuth):

```python
import employment_domain_client
from employment_domain_client.models.induction_requirement_set_v1 import InductionRequirementSetV1
from employment_domain_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://domain-adapter.internal.waooaw
# See configuration.py for a list of all supported configuration parameters.
configuration = employment_domain_client.Configuration(
    host = "https://domain-adapter.internal.waooaw"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure Bearer authorization (JWT): ServiceBearerAuth
configuration = employment_domain_client.Configuration(
    access_token = os.environ["BEARER_TOKEN"]
)

# Enter a context with an instance of the API client
with employment_domain_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = employment_domain_client.EmploymentDomainSemanticsApi(api_client)
    relationship_id = 'relationship_id_example' # str | 
    manifest_version = 'manifest_version_example' # str | 
    x_correlation_id = 'x_correlation_id_example' # str | 

    try:
        # Get profession-specific induction requirements in generic envelopes
        api_response = api_instance.get_induction_requirement_set(relationship_id, manifest_version, x_correlation_id)
        print("The response of EmploymentDomainSemanticsApi->get_induction_requirement_set:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling EmploymentDomainSemanticsApi->get_induction_requirement_set: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **relationship_id** | **str**|  | 
 **manifest_version** | **str**|  | 
 **x_correlation_id** | **str**|  | 

### Return type

[**InductionRequirementSetV1**](InductionRequirementSetV1.md)

### Authorization

[ServiceBearerAuth](../README.md#ServiceBearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json, application/problem+json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Versioned induction requirement set |  -  |
**401** | Invalid service assertion, audience, purpose or relationship delegation |  -  |
**404** | Resource absent or inaccessible |  -  |
**503** | Adapter cannot provide current domain meaning |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_performance_assessment**
> PerformanceAssessmentV1 get_performance_assessment(relationship_id, review_period_ref, x_correlation_id)

Get domain business-outcome and agent-performance meanings separately

Returns evidence-linked domain meaning without converting technical execution metrics into business outcomes.

### Example

* Bearer (JWT) Authentication (ServiceBearerAuth):

```python
import employment_domain_client
from employment_domain_client.models.performance_assessment_v1 import PerformanceAssessmentV1
from employment_domain_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://domain-adapter.internal.waooaw
# See configuration.py for a list of all supported configuration parameters.
configuration = employment_domain_client.Configuration(
    host = "https://domain-adapter.internal.waooaw"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure Bearer authorization (JWT): ServiceBearerAuth
configuration = employment_domain_client.Configuration(
    access_token = os.environ["BEARER_TOKEN"]
)

# Enter a context with an instance of the API client
with employment_domain_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = employment_domain_client.EmploymentDomainSemanticsApi(api_client)
    relationship_id = 'relationship_id_example' # str | 
    review_period_ref = 'review_period_ref_example' # str | 
    x_correlation_id = 'x_correlation_id_example' # str | 

    try:
        # Get domain business-outcome and agent-performance meanings separately
        api_response = api_instance.get_performance_assessment(relationship_id, review_period_ref, x_correlation_id)
        print("The response of EmploymentDomainSemanticsApi->get_performance_assessment:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling EmploymentDomainSemanticsApi->get_performance_assessment: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **relationship_id** | **str**|  | 
 **review_period_ref** | **str**|  | 
 **x_correlation_id** | **str**|  | 

### Return type

[**PerformanceAssessmentV1**](PerformanceAssessmentV1.md)

### Authorization

[ServiceBearerAuth](../README.md#ServiceBearerAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json, application/problem+json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Domain performance assessment |  -  |
**401** | Invalid service assertion, audience, purpose or relationship delegation |  -  |
**404** | Resource absent or inaccessible |  -  |
**503** | Adapter cannot provide current domain meaning |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **validate_plan_candidate**
> PlanValidationAssessmentV1 validate_plan_candidate(relationship_id, idempotency_key, x_correlation_id, plan_validation_request_v1)

Validate domain semantics without accepting or authorizing the plan

Assesses a candidate against admitted domain semantics while BP retains plan acceptance.

### Example

* Bearer (JWT) Authentication (ServiceBearerAuth):

```python
import employment_domain_client
from employment_domain_client.models.plan_validation_assessment_v1 import PlanValidationAssessmentV1
from employment_domain_client.models.plan_validation_request_v1 import PlanValidationRequestV1
from employment_domain_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://domain-adapter.internal.waooaw
# See configuration.py for a list of all supported configuration parameters.
configuration = employment_domain_client.Configuration(
    host = "https://domain-adapter.internal.waooaw"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure Bearer authorization (JWT): ServiceBearerAuth
configuration = employment_domain_client.Configuration(
    access_token = os.environ["BEARER_TOKEN"]
)

# Enter a context with an instance of the API client
with employment_domain_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = employment_domain_client.EmploymentDomainSemanticsApi(api_client)
    relationship_id = 'relationship_id_example' # str | 
    idempotency_key = 'idempotency_key_example' # str | 
    x_correlation_id = 'x_correlation_id_example' # str | 
    plan_validation_request_v1 = employment_domain_client.PlanValidationRequestV1() # PlanValidationRequestV1 | 

    try:
        # Validate domain semantics without accepting or authorizing the plan
        api_response = api_instance.validate_plan_candidate(relationship_id, idempotency_key, x_correlation_id, plan_validation_request_v1)
        print("The response of EmploymentDomainSemanticsApi->validate_plan_candidate:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling EmploymentDomainSemanticsApi->validate_plan_candidate: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **relationship_id** | **str**|  | 
 **idempotency_key** | **str**|  | 
 **x_correlation_id** | **str**|  | 
 **plan_validation_request_v1** | [**PlanValidationRequestV1**](PlanValidationRequestV1.md)|  | 

### Return type

[**PlanValidationAssessmentV1**](PlanValidationAssessmentV1.md)

### Authorization

[ServiceBearerAuth](../README.md#ServiceBearerAuth)

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json, application/problem+json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Domain assessment |  -  |
**400** | Invalid generic envelope or unsupported domain reference |  -  |
**401** | Invalid service assertion, audience, purpose or relationship delegation |  -  |
**409** | Idempotency, exact-version or source conflict |  -  |
**503** | Adapter cannot provide current domain meaning |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

