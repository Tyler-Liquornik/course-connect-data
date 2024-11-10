import yaml
import logging
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
from linkedin_scraper.mongo_client import get_database
from langdetect import detect
from googletrans import Translator
from bson import ObjectId


class JobProcessor:
    def __init__(self, config_path="config.yaml"):
        with open(config_path) as file:
            self.config = yaml.safe_load(file)

        if self.config.get("logging", {}).get("enabled", False):
            logging_level = self.config["logging"].get("level", "INFO").upper()
            logging.basicConfig(level=getattr(logging, logging_level))
        else:
            logging.disable(logging.CRITICAL)

        logging.info("Initializing JobTokenizer")

        self.db = get_database()
        self.jobs_collection = self.db["jobs"]

        self.nlp = spacy.load("en_core_web_sm")
        self.translator = Translator()  # Initialize Google Translator

    def detect_and_translate(self, text):
        try:
            # Detect language
            language = detect(text)
            if language == "fr":  # If text is in French
                logging.info("Translating job description from French to English")
                translated_text = self.translator.translate(text, src="fr", dest="en").text
                return translated_text
        except Exception as e:
            logging.error(f"Error detecting or translating language: {e}")

        return text  # Return original text if not in French or on failure

    def extract_keywords(self, text):
        doc = self.nlp(text)
        keywords = [ent.text for ent in doc.ents if ent.label_ in [
            "SKILL", "PROGRAMMING_LANGUAGE", "FRAMEWORK", "LIBRARY",
            "DATABASE", "CLOUD_SERVICE", "DEVOPS_TOOL", "SOFTWARE_TOOL",
            "OPERATING_SYSTEM", "METHODOLOGY", "DATA_STRUCTURE", "ALGORITHM",
            "DESIGN_PATTERN", "VERSION_CONTROL", "TESTING_FRAMEWORK", "CODE_REVIEW_TOOL",
            "BUILD_TOOL", "API_TECHNOLOGY", "SECURITY_PROTOCOL", "NETWORKING_TECH",
            "FRONTEND_TECH", "BACKEND_TECH", "DATA_ANALYSIS_TOOL", "CONTAINERIZATION",
            "ORCHESTRATION", "MACHINE_LEARNING_LIB"
        ]]

        if len(keywords) < 5:
            tfidf = TfidfVectorizer(max_features=25, stop_words="english")
            tfidf.fit_transform([text])
            keywords.extend(tfidf.get_feature_names_out().tolist())

        return list(set(keywords))  # Return unique keywords

    def process_jobs(self, job_ids):
        logging.info("Starting Keyword Extraction for specified job descriptions")

        for job_id in job_ids:
            job = self.jobs_collection.find_one({"_id": ObjectId(job_id)})
            if not job:
                logging.warning(f"Job with ID {job_id} not found.")
                continue

            job_description = job.get("job_description", "")
            if not job_description:
                logging.warning(f"Job ID {job_id} has no job description.")
                continue

            # Detect and translate if necessary
            translated_description = self.detect_and_translate(job_description)

            # Use translated description for keywords if translation occurred
            description_to_analyze = translated_description if translated_description != job_description else job_description
            keywords = self.extract_keywords(description_to_analyze)
            logging.info(f"Extracted keywords for Job ID {job_id}: {keywords}")

            # Update MongoDB with keywords and translated description if necessary
            update_data = {"keywords": keywords}
            if translated_description != job_description:
                update_data["translated_description"] = translated_description

            self.jobs_collection.update_one(
                {"_id": ObjectId(job_id)},
                {"$set": update_data}
            )

        logging.info("Keyword extraction and MongoDB update complete!")
