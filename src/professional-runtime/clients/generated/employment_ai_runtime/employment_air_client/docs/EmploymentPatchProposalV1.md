# EmploymentPatchProposalV1


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**schema_version** | [**AirEmploymentSchemaVersion**](AirEmploymentSchemaVersion.md) |  | 
**proposal_id** | **str** |  | 
**protocol_version** | **str** |  | 
**relationship_ref** | **str** |  | 
**contribution_ref** | **str** |  | 
**agent_type** | **str** |  | 
**agent_version** | **str** |  | 
**manifest_version** | **str** |  | 
**semantic_catalogue** | [**ImmutableContractReferenceV1**](ImmutableContractReferenceV1.md) |  | 
**request_digest** | **str** |  | 
**patch_type** | [**ProposalPatchType**](ProposalPatchType.md) |  | 
**state** | [**ProposalState**](ProposalState.md) |  | 
**operations** | [**List[ProposalOperation]**](ProposalOperation.md) |  | 
**confidence** | **float** |  | 
**assumptions** | **List[str]** |  | 
**unresolved_questions** | **List[str]** |  | 
**source_refs** | **List[str]** |  | 
**prompt_policy** | [**ImmutableContractReferenceV1**](ImmutableContractReferenceV1.md) |  | 
**model_policy** | [**ImmutableContractReferenceV1**](ImmutableContractReferenceV1.md) |  | 
**model_decision_ref** | **str** | Privacy-minimised provider-selection evidence reference. | 
**reason_code** | **str** |  | [optional] 
**produced_at** | **datetime** |  | 

## Example

```python
from employment_air_client.models.employment_patch_proposal_v1 import EmploymentPatchProposalV1

# TODO update the JSON string below
json = "{}"
# create an instance of EmploymentPatchProposalV1 from a JSON string
employment_patch_proposal_v1_instance = EmploymentPatchProposalV1.from_json(json)
# print the JSON string representation of the object
print(EmploymentPatchProposalV1.to_json())

# convert the object into a dict
employment_patch_proposal_v1_dict = employment_patch_proposal_v1_instance.to_dict()
# create an instance of EmploymentPatchProposalV1 from a dict
employment_patch_proposal_v1_from_dict = EmploymentPatchProposalV1.from_dict(employment_patch_proposal_v1_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


