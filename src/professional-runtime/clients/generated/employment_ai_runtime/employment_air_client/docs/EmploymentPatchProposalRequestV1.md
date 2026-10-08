# EmploymentPatchProposalRequestV1


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**schema_version** | [**AirEmploymentSchemaVersion**](AirEmploymentSchemaVersion.md) |  | 
**protocol_version** | **str** |  | 
**relationship_ref** | **str** | PR-issued opaque reference; not a customer identifier. | 
**contribution_ref** | **str** |  | 
**agent_type** | **str** |  | 
**agent_version** | **str** |  | 
**manifest_version** | **str** |  | 
**semantic_catalogue** | [**ImmutableContractReferenceV1**](ImmutableContractReferenceV1.md) |  | 
**prompt_policy** | [**ImmutableContractReferenceV1**](ImmutableContractReferenceV1.md) |  | 
**model_policy** | [**ImmutableContractReferenceV1**](ImmutableContractReferenceV1.md) |  | 
**patch_type** | [**ProposalPatchType**](ProposalPatchType.md) |  | 
**request_digest** | **str** | Canonical SHA-256 digest of the immutable request identity and payload, excluding this field. | 
**contribution** | [**EmploymentPatchProposalRequestV1Contribution**](EmploymentPatchProposalRequestV1Contribution.md) |  | 
**bounded_context** | [**EmploymentPatchProposalRequestV1BoundedContext**](EmploymentPatchProposalRequestV1BoundedContext.md) |  | [optional] 

## Example

```python
from employment_air_client.models.employment_patch_proposal_request_v1 import EmploymentPatchProposalRequestV1

# TODO update the JSON string below
json = "{}"
# create an instance of EmploymentPatchProposalRequestV1 from a JSON string
employment_patch_proposal_request_v1_instance = EmploymentPatchProposalRequestV1.from_json(json)
# print the JSON string representation of the object
print(EmploymentPatchProposalRequestV1.to_json())

# convert the object into a dict
employment_patch_proposal_request_v1_dict = employment_patch_proposal_request_v1_instance.to_dict()
# create an instance of EmploymentPatchProposalRequestV1 from a dict
employment_patch_proposal_request_v1_from_dict = EmploymentPatchProposalRequestV1.from_dict(employment_patch_proposal_request_v1_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


