data/raw_datasets/${NUM}:
	python3 scripts/data_creation/dataset_creation.py --number_of_equations $${NUM:0:$${#NUM}-1}000 --no-debug

data/datasets/${NUM}/.dirstamp: data/raw_datasets/${NUM}
	python3 scripts/data_creation/split_train_val.py --data_path $?

