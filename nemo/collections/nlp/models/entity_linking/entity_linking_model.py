import torch
from pytorch_lightning import Trainer
from typing import Optional, Dict, List
from omegaconf import DictConfig, OmegaConf
from transformers import AutoTokenizer
from nemo.collections.nlp.models.nlp_model import NLPModel
from nemo.collections.nlp.modules.common.lm_utils import get_lm_model
from nemo.collections.nlp.data import EntityLinkingDataset
from nemo.collections.common.losses import MultiSimilarityLoss
from nemo.core.classes.exportable import Exportable
from nemo.core.neural_types import NeuralType, ChannelType, MaskType, LogitsType
from nemo.core.classes.common import typecheck
from nemo.utils import logging

__all__ = ['EntityLinkingModel']

class EntityLinkingModel(NLPModel, Exportable):
    """
    Second stage pretraining of BERT based language model
    for entity linking task.
    """

    @property
    def input_types(self) -> Optional[Dict[str, NeuralType]]:
        return {
            "input_ids": NeuralType(('B', 'T'), ChannelType()),
            "attention_mask": NeuralType(('B', 'T'), MaskType(), optional=True),
            "token_type_ids": NeuralType(('B', 'T'), ChannelType(), optional=True),
        }

    @property 
    def output_types(self) -> Optional[Dict[str, NeuralType]]:
        return {"logits": NeuralType(('B', 'D'), LogitsType())}


    def __init__(self, cfg: DictConfig, trainer: Trainer = None):
        """Initializes the SAP-BERT model for entity linking."""

        # tokenizer needed before super().__init__() so dataset and loader can process data
        self._setup_tokenizer(cfg.tokenizer)

        super().__init__(cfg=cfg, trainer=trainer)

        self.model = get_lm_model(
            pretrained_model_name=cfg.language_model.pretrained_model_name,
            config_file=cfg.language_model.config_file,
            config_dict=cfg.language_model.config,
            checkpoint_file=cfg.language_model.lm_checkpoint,
        )

        # Token to use for the self-alignment loss, typically the first token, [CLS]
        self._idx_conditioned_on = 0
        self.loss = MultiSimilarityLoss()
        self.index = None

    def _setup_tokenizer(self, cfg: DictConfig):
        tokenizer = AutoTokenizer.from_pretrained(
            cfg.tokenizer_name,
            vocab_file=cfg.vocab_file,
            do_lower_case=cfg.do_lower_case)

        self.tokenizer = tokenizer
        
    @typecheck()
    def forward(self, input_ids, token_type_ids, attention_mask):
        hidden_states = self.model(
            input_ids=input_ids, token_type_ids=token_type_ids, attention_mask=attention_mask
        )

        # normalize to unit sphere
        logits = torch.nn.functional.normalize(hidden_states[:,self._idx_conditioned_on], p=2, dim=1)
        return logits

    def training_step(self, batch, batch_idx):
        """
        Lightning calls this inside the training loop with the data from the training dataloader
        passed in as `batch`.
        """
        input_ids, token_type_ids, attention_mask, concept_ids = batch
        logits = self.forward(input_ids=input_ids, token_type_ids=token_type_ids, attention_mask=attention_mask)
        train_loss = self.loss(logits=logits, labels=concept_ids)

        # No hard examples found in batch, 
        # shouldn't use this batch to update model weights
        if train_loss == 0:
            train_loss = None
            lr = None

        else:
            lr = self._optimizer.param_groups[0]["lr"]
            self.log("train_loss", train_loss)
            self.log("lr", lr, prog_bar=True)

        return {"loss": train_loss, "lr": lr}

    def validation_step(self, batch, batch_idx):
        """
        Lightning calls this inside the validation loop with the data from the validation dataloader
        passed in as `batch`.
        """
        input_ids, input_type_ids, input_mask, concept_ids = batch
        with torch.no_grad():
            logits = self.forward(input_ids=input_ids, token_type_ids=input_type_ids, attention_mask=input_mask)
            val_loss = self.loss(logits=logits, labels=concept_ids)

        # No hard examples found in batch, 
        # shouldn't use this batch to update model weights
        if val_loss == 0:
            val_loss = None
        else:
            self.log("val_loss", val_loss)
            logging.info(f"val loss: {val_loss}")

        return {"val_loss": val_loss}

    def validation_epoch_end(self, outputs):
        """
        Called at the end of validation to aggregate outputs.

        Args:
            outputs: list of individual outputs of each validation step.
        Returns:
            
        """
        if outputs:
            avg_loss = torch.stack([x["val_loss"] for x in outputs if x["val_loss"] != None]).mean()
            self.log(f"val_loss", avg_loss, prog_bar=True)
            
            return {"val_loss": avg_loss}


    def setup_training_data(self, train_data_config: Optional[DictConfig]):
        if not train_data_config or not train_data_config.data_file:
            logging.info(
                f"Dataloader config or file_path or processed data path for the train dataset is missing, \
                        so no data loader for train is created!"
            )

            self._train_dl = None
            return

        self._train_dl = self.setup_dataloader(cfg=train_data_config)

    def setup_validation_data(self, val_data_config: Optional[DictConfig]):
        if not val_data_config or not val_data_config.data_file:
            logging.info(
                f"Dataloader config or file_path or processed data path for the val dataset is missing, \
                        so no data loader for validation is created!"
            )

            self._validation_dl = None
            return

        self._validation_dl = self.setup_dataloader(cfg=val_data_config)

    def setup_dataloader(self, cfg: Dict, is_index_data: bool = False) -> 'torch.utils.data.DataLoader':
        
        dataset = EntityLinkingDataset( 
                tokenizer=self.tokenizer,
                data_file=cfg.data_file,
                max_seq_length=cfg.max_seq_length,
                is_index_data=is_index_data,
            )
    
        return torch.utils.data.DataLoader(
                dataset=dataset,
                batch_size=cfg.batch_size,
                collate_fn=dataset.collate_fn,
                shuffle=cfg.get("shuffle", True),
                num_workers=cfg.get("num_wokers", 2),
                pin_memory=cfg.get("pin_memory", False),
                drop_last=cfg.get("drop_last", False)
                )

    @classmethod
    def list_available_models(cls) -> Optional[Dict[str, str]]:
        pass

    @classmethod
    def from_pretrained(cls, name: str):
        pass

