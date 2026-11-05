"""UI authentication without persisting credentials or browser state."""

import re

from playwright.sync_api import Page, expect

from config.settings import Settings


class LoginPage:
    def __init__(self, page: Page) -> None:
        self.page = page

    def sign_in(self, settings: Settings) -> None:
        self.page.goto(f"{settings.base_url}/login")
        self.page.get_by_label(re.compile(r"^(Email|E-Mail)$", re.I)).filter(
            visible=True
        ).fill(settings.username)
        self.page.get_by_label(re.compile(r"^(Password|Senha)$", re.I)).filter(
            visible=True
        ).fill(settings.password)
        self.page.get_by_role(
            "button", name=re.compile(r"^(Continue|Continuar)$", re.I)
        ).click()
        expect(self.page).to_have_url(
            re.compile(r"^" + re.escape(settings.base_url) + r"/desk(?:/[^?#]*)?(?:[?#].*)?$")
        )

    def enter_erpnext(self, base_url: str) -> None:
        launcher = self.page.get_by_role("link", name="ERPNext", exact=True).filter(visible=True)
        buying = self.page.get_by_role("button", name="Buying", exact=True).filter(visible=True)
        # Wait for a recognized state, not an immediate snapshot during redirect/render.
        expect(launcher.or_(buying)).not_to_have_count(0)
        if launcher.is_visible():
            launcher.click()

        # Both legitimate branches must finish inside a known ERPNext workspace.
        modules = "setup|accounts|selling|buying|stock|manufacturing|projects|assets|quality"
        expect(self.page).to_have_url(
            re.compile(
                r"^" + re.escape(base_url)
                + rf"/desk/(?:{modules})(?:/[^?#]+)?(?:[?#].*)?$"
            )
        )
        expect(self.page.get_by_role("link", name="Home", exact=True)).to_be_visible()

    def assert_workspaces_available(self) -> None:
        expect(self.page.get_by_role("button", name="Buying", exact=True)).to_be_visible()
        expect(self.page.get_by_role("button", name="Stock", exact=True)).to_be_visible()
