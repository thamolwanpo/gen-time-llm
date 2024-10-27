"""Torch Dataset for Time Series"""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/tsdataset.ipynb.

# %% auto 0
__all__ = ['TimeSeriesLoader', 'TimeSeriesDataset', 'TimeSeriesDataModule']

# %% ../nbs/tsdataset.ipynb 4
import warnings
import re
import torch
import json
from collections.abc import Mapping
from torch.utils.data import Dataset, DataLoader
import pytorch_lightning as pl

# %% ../nbs/tsdataset.ipynb 5
class TimeSeriesLoader(DataLoader):
    """TimeSeriesLoader DataLoader.
    
    Custom DataLoader to work with time series datasets, handling dynamic padding for tokenized summaries and attention masks,
    and using the tokenizer's `eos_token_id` for padding.
    """
    
    def __init__(self, dataset, tokenizer, **kwargs):
        """
        Initializes the loader with the dataset and tokenizer.
        
        Parameters:
        - dataset: The TimeSeriesDataset instance.
        - tokenizer: The tokenizer used for tokenizing summaries (e.g., from HuggingFace's Transformers library).
        """
        self.tokenizer = tokenizer  # Store the tokenizer for eos_token_id
        if 'collate_fn' in kwargs:
            kwargs.pop('collate_fn')
        kwargs_ = {**kwargs, **dict(collate_fn=self._collate_fn)}
        super().__init__(dataset=dataset, **kwargs_)
    
    def _collate_fn(self, batch):
        """
        Custom collate function to handle time series data and dynamically pad tokenized summaries with `eos_token_id`.
        """
        elem = batch[0]
        elem_type = type(elem)

        # Handle case when the batch is a tensor (e.g., temporal series)
        if isinstance(elem, torch.Tensor):
            return torch.stack(batch, dim=0)

        # Handle case when the batch is a dictionary
        elif isinstance(elem, Mapping):
            # Collate temporal series (stack 2D time series tensors)
            temporal_series = self.collate_fn([d['temporal_series'] for d in batch])
            
            # Collate sector information (as a list)
            sector = [d['sector'] for d in batch]
            
            # Find the maximum sequence length in the current batch for dynamic padding
            max_length = max([d['summary_input_ids'].size(0) for d in batch])
            
            # Dynamically pad summaries using eos_token_id
            eos_token_id = self.tokenizer.eos_token_id
            summary_input_ids = torch.stack([torch.cat([d['summary_input_ids'], 
                                                        torch.full((max_length - d['summary_input_ids'].size(0),), 
                                                                   eos_token_id, dtype=torch.long)])
                                             for d in batch])
            
            # Dynamically pad attention masks (using 0 for padding)
            attention_mask = None
            if batch[0]['attention_mask'] is not None:
                attention_mask = torch.stack([torch.cat([d['attention_mask'], 
                                                         torch.zeros(max_length - d['attention_mask'].size(0), 
                                                                     dtype=torch.long)])
                                              for d in batch])
            
            # Collate country information (keeping as list of strings)
            country = [d['country'] for d in batch]
            
            # Collate columns of temporal data (should remain consistent across batch)
            temporal_cols = batch[0]['temporal_cols']

            # Return the collated batch with dynamic padding for tokenized summaries
            return dict(
                temporal_series=temporal_series,
                sector=sector,
                summary_input_ids=summary_input_ids,
                attention_mask=attention_mask,
                country=country,
                temporal_cols=temporal_cols
            )

        # Raise error if an unsupported data type is passed
        raise TypeError(f'Unknown type {elem_type}')

# %% ../nbs/tsdataset.ipynb 7
class TimeSeriesDataset(Dataset):
    def __init__(self,
                 data_list,  # List of dictionaries containing time series and metadata
                 tokenizer,  # Tokenizer for summarizing text (e.g., from HuggingFace's Transformers library)
                 max_length: int = 512,  # Max token length for tokenization
                 sorted=False,  # Whether the dataset is already sorted
                 add_attention_mask: bool = True  # Whether to include attention mask for tokenized summaries
                ):
        """
        A dataset class for structured time series data, with both temporal and static (text) features.
        
        Parameters:
        - data_list: List of dictionaries, where each dictionary contains keys like:
            - 'anchor_summary': Short description or metadata (to be tokenized).
            - 'positive_time_series': 2D array of temporal data for the entity.
            - 'positive_sector': One-hot encoded sector information.
            - 'sector': Sectors assigned to this time series (as string).
            - 'country': Country associated with the time series.
            - 'columns': Names of the temporal columns/features.
        - tokenizer: Tokenizer instance for encoding the summaries (e.g., GPT tokenizer or any other transformer model).
        - max_length: Maximum length for the tokenized summaries (default: 512).
        - sorted: Whether the dataset is already sorted (default: False).
        - add_attention_mask: Whether to add an attention mask for tokenized summaries (default: True).
        """
        super().__init__()
        
        self.data_list = data_list
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.sorted = sorted
        self.add_attention_mask = add_attention_mask
        self.n_groups = len(self.data_list)  # Number of time series entities

    def clean_text(self, text):
        # Remove duplicate spaces and newlines
        text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with a single space
        text = text.replace('\n', ' ')  # Replace newlines with a space
        text = text.strip()  # Remove leading and trailing spaces
        return text

    def __len__(self):
        """
        Return the number of time series entities in the dataset.
        """
        return self.n_groups
    
    def __getitem__(self, idx):
        """
        Return a single item from the dataset (time series and its metadata).
        The index `idx` specifies which time series entity to retrieve.
        """
        data = self.data_list[idx]
        
        # Extract fields from the dictionary
        temporal_series = torch.tensor(data['positive_time_series'], dtype=torch.float32)
        anchor_summary = self.clean_text(data['anchor_summary'])
        country = data['country']
        columns = data['columns']
        sector_str = data['sector']  # This is a string representation of sectors

        # Tokenize the summary with the specified tokenizer
        tokenized_summary = self.tokenizer(
            anchor_summary,
            max_length=self.max_length,
            truncation=True,
            return_tensors='pt'  # Return PyTorch tensors
        )

        # Extract tokenized input_ids and attention mask (optional)
        input_ids = tokenized_summary['input_ids'].squeeze(0)  # Remove batch dimension
        attention_mask = tokenized_summary['attention_mask'].squeeze(0) if self.add_attention_mask else None

        # Return a dictionary with both temporal and static features, including tokenized summary
        return {
            'temporal_series': temporal_series,  # 2D time series data
            'sector': sector_str,                # Sectors as string
            'summary_input_ids': input_ids,      # Tokenized summary
            'attention_mask': attention_mask,    # Attention mask (if applicable)
            'country': country,                  # Static feature (country)
            'temporal_cols': columns             # Names of temporal features
        }
    
    def __repr__(self):
        """
        Return a string representation of the dataset, showing the number of data points and groups.
        """
        return f"TimeSeriesDataset(n_data={len(self.data_list):,}, n_groups={self.n_groups:,})"

    def __eq__(self, other):
        """
        Check if two datasets are equal by comparing their data and attributes.
        """
        if not isinstance(other, TimeSeriesDataset):
            return False
        return (
            self.data_list == other.data_list and
            self.max_length == other.max_length and
            self.sorted == other.sorted
        )
    
    @staticmethod
    def from_jsonl(file_path, tokenizer, max_length=512, sorted=False, add_attention_mask=True):
        """
        Static method to load time series data from a JSONL file.
        
        Parameters:
        - file_path: Path to the JSONL file.
        - tokenizer: Tokenizer to use for tokenizing the summaries.
        - max_length: Maximum token length for the summaries.
        - sorted: Whether the dataset should be sorted.
        - add_attention_mask: Whether to include attention masks for tokenized summaries.

        Returns:
        - dataset: TimeSeriesDataset instance with loaded data.
        """
        # Load the JSONL file
        data_list = []
        with open(file_path, 'r') as f:
            for line in f:
                data_list.append(json.loads(line))

        # Create and return the dataset instance
        return TimeSeriesDataset(
            data_list=data_list,
            tokenizer=tokenizer,
            max_length=max_length,
            sorted=sorted,
            add_attention_mask=add_attention_mask
        )

# %% ../nbs/tsdataset.ipynb 10
class TimeSeriesDataModule(pl.LightningDataModule):
    
    def __init__(
            self, 
            train_dataset: TimeSeriesDataset,  # Separate dataset for training
            val_dataset: TimeSeriesDataset,    # Separate dataset for validation
            tokenizer,                         # Tokenizer for all datasets
            batch_size=32, 
            valid_batch_size=8,
            num_workers=0,
            drop_last=False,
            shuffle_train=True,
            test_dataset: TimeSeriesDataset = None,   # Separate dataset for testing (optional)
        ):
        """
        A DataModule for loading time series data, supporting training, validation, and prediction.
        
        Parameters:
        - train_dataset: The TimeSeriesDataset instance for the training data.
        - val_dataset: The TimeSeriesDataset instance for the validation data.
        - test_dataset: The TimeSeriesDataset instance for the test data (optional).
        - tokenizer: The tokenizer used for tokenizing summaries (e.g., from HuggingFace's Transformers library).
        - batch_size: Batch size for the training data.
        - valid_batch_size: Batch size for the validation and test data.
        - num_workers: Number of workers for data loading (default: 0).
        - drop_last: Whether to drop the last incomplete batch (default: False).
        - shuffle_train: Whether to shuffle the training data (default: True).
        """
        super().__init__()
        self.train_dataset = train_dataset
        self.val_dataset = val_dataset
        self.test_dataset = test_dataset
        self.tokenizer = tokenizer
        self.batch_size = batch_size
        self.valid_batch_size = valid_batch_size
        self.num_workers = num_workers
        self.drop_last = drop_last
        self.shuffle_train = shuffle_train

        self.tokenizer.pad_token = self.tokenizer.eos_token  # Ensure padding token is set
    
    def train_dataloader(self):
        """
        Creates and returns a DataLoader for the training dataset.
        """
        loader = TimeSeriesLoader(
            self.train_dataset,
            tokenizer=self.tokenizer,  # Pass the tokenizer
            batch_size=self.batch_size, 
            num_workers=self.num_workers,
            shuffle=self.shuffle_train,
            drop_last=self.drop_last
        )
        return loader
    
    def val_dataloader(self):
        """
        Creates and returns a DataLoader for the validation dataset.
        """
        loader = TimeSeriesLoader(
            self.val_dataset, 
            tokenizer=self.tokenizer,  # Pass the tokenizer
            batch_size=self.valid_batch_size, 
            num_workers=self.num_workers,
            shuffle=False,
            drop_last=self.drop_last
        )
        return loader
    
    def test_dataloader(self):
        """
        Creates and returns a DataLoader for the test dataset.
        """
        if self.test_dataset:
            loader = TimeSeriesLoader(
                self.test_dataset,
                tokenizer=self.tokenizer,  # Pass the tokenizer
                batch_size=self.valid_batch_size, 
                num_workers=self.num_workers,
                shuffle=False
            )
            return loader
        return None
