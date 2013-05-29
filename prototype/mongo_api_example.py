running_t.insert(uuid=911, user_id="1@1.com", instance_data={"image_id": 123})
pp(running_t.query(uuid=911))
running_t.delete(uuid=918)
running_t.update(dict(uuid=912), new_field="123121111111111111113")