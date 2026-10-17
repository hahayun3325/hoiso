import base64,copy,json,unittest
import mask_validation as v

class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.protocol=dict(case_id='synthetic_test',selected_hand_id='test',image_binding=v.binding(b'RGB'),policy=v.POLICY)
        self.labels=bytes([255,255,0,128])+bytes(v.N-4)
        self.record=dict(schema='tracehoi.IndependentMaskReference.v1',context=v.reference_context(self.protocol),state='complete',annotator='Synthetic test fixture',annotated_at='2026-10-17T22:00:00Z',method='manual_rgb_delineation',candidate_mask_used=False,model_assistance_used=False,prior_candidate_exposure='yes',whole_image_inspected=True,notes='Synthetic test pixels, not a human annotation.',labels_base64=base64.b64encode(self.labels).decode())
    def validate(self,**updates):
        r=dict(self.record);r.update(updates);return v.validate_reference(v.encode(r),self.protocol)
    def test_valid_reference_preserves_fields(self):self.assertEqual(self.validate(),(self.record,self.labels))
    def test_draft_refused(self):
        with self.assertRaisesRegex(ValueError,'completed_reference'):self.validate(state='draft')
    def test_wrong_image_refused(self):
        c=copy.deepcopy(self.record['context']);c['image_binding']=v.binding(b'other')
        with self.assertRaisesRegex(ValueError,'context'):self.validate(context=c)
    def test_changed_protocol_refused(self):
        p=dict(self.protocol,policy='changed')
        with self.assertRaisesRegex(ValueError,'context'):v.validate_reference(v.encode(self.record),p)
    def test_candidate_tracing_refused(self):
        with self.assertRaisesRegex(ValueError,'separate_reference'):self.validate(candidate_mask_used=True)
    def test_model_assistance_refused(self):
        with self.assertRaisesRegex(ValueError,'separate_reference'):self.validate(model_assistance_used=True)
    def test_numeric_false_is_not_boolean(self):
        with self.assertRaisesRegex(ValueError,'separate_reference'):self.validate(candidate_mask_used=0)
    def test_prior_exposure_required(self):
        with self.assertRaisesRegex(ValueError,'prior_exposure'):self.validate(prior_candidate_exposure='blind')
    def test_missing_annotator(self):
        with self.assertRaisesRegex(ValueError,'annotator'):self.validate(annotator=' ')
    def test_missing_boundary_notes(self):
        with self.assertRaisesRegex(ValueError,'notes'):self.validate(notes='')
    def test_naive_time_refused(self):
        with self.assertRaisesRegex(ValueError,'timezone'):self.validate(annotated_at='2026-10-17T22:00:00')
    def test_invalid_time_refused(self):
        with self.assertRaisesRegex(ValueError,'time'):self.validate(annotated_at='yesterday')
    def test_uninspected_refused(self):
        with self.assertRaisesRegex(ValueError,'inspection'):self.validate(whole_image_inspected=False)
    def test_extra_acceptance_field_refused(self):
        with self.assertRaisesRegex(ValueError,'fields'):self.validate(placement_ready=True)
    def test_wrong_shape_refused(self):
        with self.assertRaisesRegex(ValueError,'encoding_size'):self.validate(labels_base64=base64.b64encode(b'\0').decode())
    def test_wrong_labels_refused(self):
        with self.assertRaisesRegex(ValueError,'ternary'):self.validate(labels_base64=base64.b64encode(bytes([1])+self.labels[1:]).decode())
    def test_invalid_base64_refused(self):
        with self.assertRaisesRegex(ValueError,'encoding'):self.validate(labels_base64='!'*349528)
    def test_empty_foreground_refused(self):
        with self.assertRaisesRegex(ValueError,'foreground'):self.validate(labels_base64=base64.b64encode(bytes(v.N)).decode())
    def test_full_foreground_refused(self):
        with self.assertRaisesRegex(ValueError,'background'):self.validate(labels_base64=base64.b64encode(bytes([255])*v.N).decode())
    def test_duplicate_json_key_refused(self):
        with self.assertRaisesRegex(ValueError,'duplicate_key'):v.parse(b'{"x":1,"x":2}')
    def test_nonfinite_refused(self):
        with self.assertRaisesRegex(ValueError,'nonfinite'):v.parse(b'{"x":NaN}')
    def test_known_confusion_counts(self):
        pred=bytes([255,0,255,255])+bytes(v.N-4);m=v.score(pred,self.labels,bytes(v.N))
        self.assertEqual([m[k] for k in ['tp','fn','fp','tn']],[1,1,1,v.N-4]);self.assertEqual(m['iou'],1/3);self.assertEqual(m['dice'],.5);self.assertEqual(m['precision'],.5);self.assertEqual(m['recall'],.5);self.assertEqual(m['evaluated_pixels'],v.N-1)
    def test_overlap_and_uncertainty_union(self):
        m=v.score(bytes([255])*v.N,self.labels,bytes([255,0,0,255])+bytes(v.N-4))
        self.assertEqual(m['fixed_overlap_excluded_pixels'],2);self.assertEqual(m['reference_uncertain_pixels'],1);self.assertEqual(m['reference_uncertain_outside_overlap'],0);self.assertEqual(m['evaluated_pixels'],v.N-2)
    def test_zero_denominator_is_null(self):
        m=v.score(bytes(v.N),bytes(v.N),bytes(v.N));self.assertIsNone(m['iou']);self.assertIsNone(m['precision']);self.assertIsNone(m['recall'])
    def test_all_ignored_is_unscored(self):
        m=v.score(bytes(v.N),bytes([128])*v.N,bytes(v.N));self.assertEqual(m['evaluated_fraction'],0);self.assertIsNone(m['dice'])
    def test_perfect_match(self):
        b=bytes([255,0])+bytes(v.N-2);m=v.score(b,b,bytes(v.N));self.assertEqual(m['iou'],1);self.assertEqual(m['dice'],1)
    def test_shape_refused(self):
        with self.assertRaisesRegex(ValueError,'shape'):v.score(b'',b'',b'')
    def test_nonbinary_candidate_refused(self):
        with self.assertRaisesRegex(ValueError,'values'):v.score(bytes([1])*v.N,self.labels,bytes(v.N))
    def test_annotation_contains_rgb_context_only(self):
        raw=v.annotation_html(v.reference_context(self.protocol),b'RGB',dict(scope='test'))
        data=json.loads(raw.decode().split('<script id="data" type="application/json">')[1].split('</script>')[0]);self.assertEqual(set(data),{'context','rgb','scope'});self.assertNotIn('working_mask_binding',data['context'])
    def test_html_script_injection_escaped(self):
        raw=v.annotation_html(v.reference_context(self.protocol),b'RGB',dict(scope='</script><script>alert(1)</script>'));self.assertNotIn(b'</script><script>alert',raw)

if __name__=='__main__':unittest.main(verbosity=2)
