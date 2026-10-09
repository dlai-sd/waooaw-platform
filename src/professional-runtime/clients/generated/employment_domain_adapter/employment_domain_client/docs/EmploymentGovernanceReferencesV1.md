# EmploymentGovernanceReferencesV1


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**agent_specification** | [**ImmutableContractReferenceV1**](ImmutableContractReferenceV1.md) |  | 
**prompt_policy** | [**ImmutableContractReferenceV1**](ImmutableContractReferenceV1.md) |  | 
**tool_profile** | [**ImmutableContractReferenceV1**](ImmutableContractReferenceV1.md) |  | 
**decision_consequence_map** | [**ImmutableContractReferenceV1**](ImmutableContractReferenceV1.md) |  | 

## Example

```python
from employment_domain_client.models.employment_governance_references_v1 import EmploymentGovernanceReferencesV1

# TODO update the JSON string below
json = "{}"
# create an instance of EmploymentGovernanceReferencesV1 from a JSON string
employment_governance_references_v1_instance = EmploymentGovernanceReferencesV1.from_json(json)
# print the JSON string representation of the object
print(EmploymentGovernanceReferencesV1.to_json())

# convert the object into a dict
employment_governance_references_v1_dict = employment_governance_references_v1_instance.to_dict()
# create an instance of EmploymentGovernanceReferencesV1 from a dict
employment_governance_references_v1_from_dict = EmploymentGovernanceReferencesV1.from_dict(employment_governance_references_v1_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


